"""Consolidate Conditional Expression refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_range
from molting.core.code_generation_utils import create_parameter
from molting.core.local_variable_analyzer import LocalVariableAnalyzer
from molting.core.visitors import MethodConflictChecker


class ConsolidateConditionalExpressionCommand(BaseCommand):
    """Consolidate multiple conditionals with identical results into a single expression.

    This refactoring combines a sequence of conditional tests that all return the
    same result into a single conditional expression. Multiple separate if statements
    checking different conditions but performing the same action are replaced with
    a single if statement that combines all conditions using logical operators (or).
    This improves code clarity by making the intent of the code more explicit and
    reducing duplication.

    **When to use:**
    - You have multiple if statements checking different conditions with identical results
    - Several boolean expressions lead to the same return value or action
    - You want to make the logical structure of conditional logic more apparent
    - You need to reduce redundancy in conditional chains

    **Example:**

    Before:
        def discount(customer):
            if customer.type == "valued":
                return 0.05
            if customer.type == "premium":
                return 0.05
            if customer.loyalty_years > 10:
                return 0.05
            return 0.0

    After:
        def discount(customer):
            if is_eligible(customer):
                return 0.05
            return 0.0

        def is_eligible(customer):
            return (customer.type == "valued" or
                    customer.type == "premium" or
                    customer.loyalty_years > 10)
    """

    name = "consolidate-conditional-expression"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply consolidate-conditional-expression refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        helper_name = self.params["name"]

        # Parse target format: "function_name#L2-L7" or "ClassName::method#L2-L7"
        class_name, function_name, start_line, end_line = self._parse_target(target)

        # Read file
        source_code = self.file_path.read_text()

        # Parse module
        module = cst.parse_module(source_code)

        # Check for name conflicts - helper function/method should not already exist
        conflict_checker = MethodConflictChecker(class_name, helper_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            if class_name:
                raise ValueError(
                    f"Method '{helper_name}' already exists in class '{class_name}'"
                )
            else:
                raise ValueError(f"Function '{helper_name}' already exists")

        # Parse and transform with metadata
        wrapper = metadata.MetadataWrapper(module)
        transformer = ConsolidateConditionalExpressionTransformer(
            class_name, function_name, start_line, end_line, helper_name, module
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)

    def _parse_target(self, target: str) -> tuple[str, str, int, int]:
        """Parse target format into class name, function name, and line range.

        Args:
            target: Target string in format "function_name#L2-L5" or "ClassName::method#L2-L5"

        Returns:
            Tuple of (class_name, function_name, start_line, end_line)
            class_name will be empty string for module-level functions

        Raises:
            ValueError: If target format is invalid
        """
        parts = target.split("#")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid target format '{target}'. "
                "Expected 'function_name#L2-L5' or 'ClassName::method#L2-L5'"
            )

        class_method = parts[0]
        line_spec = parts[1]

        # Parse class_method to extract class and method names
        if "::" in class_method:
            class_parts = class_method.split("::")
            if len(class_parts) != 2:
                raise ValueError(f"Invalid class::method format in '{class_method}'")
            class_name, function_name = class_parts
        else:
            class_name = ""
            function_name = class_method

        start_line, end_line = parse_line_range(line_spec)
        return class_name, function_name, start_line, end_line


class ConsolidateConditionalExpressionTransformer(cst.CSTTransformer):
    """Transforms sequential if statements into a consolidated conditional."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        class_name: str,
        function_name: str,
        start_line: int,
        end_line: int,
        helper_name: str,
        module: cst.Module | None = None,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class (empty string for module-level functions)
            function_name: Name of the function to refactor
            start_line: Start line of the conditional range
            end_line: End line of the conditional range
            helper_name: Name of the helper function to create
            module: The CST module for analyzing local variables
        """
        self.class_name = class_name
        self.function_name = function_name
        self.start_line = start_line
        self.end_line = end_line
        self.helper_name = helper_name
        self.module = module
        self.conditions: list[cst.BaseExpression] = []
        self.return_value: cst.BaseExpression | None = None
        self.helper_function: cst.FunctionDef | None = None
        self.num_ifs_to_replace = 0
        self.current_function: str | None = None
        self.current_class: str | None = None
        self.function_params: list[str] = []
        self.local_variables: list[str] = []
        self.variables_used_in_conditions: list[str] = []
        self._is_method = False
        self._first_param: cst.Param | None = None
        self._second_param: cst.Param | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track current class being visited."""
        if node.name.value == self.class_name:
            self.current_class = self.class_name
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to find target function."""
        self.current_function = node.name.value
        if node.name.value == self.function_name:
            # Check if this is a class method
            if self.class_name and self.current_class == self.class_name:
                self._is_method = True
            elif not self.class_name:
                self._is_method = False

            # Collect function parameter names
            for param in node.params.params:
                self.function_params.append(param.name.value)

            # Store parameters for helper function
            if node.params.params:
                self._first_param = node.params.params[0]
                if len(node.params.params) > 1:
                    self._second_param = node.params.params[1]

            # Analyze local variables early
            if self.module and not self.local_variables:
                analyzer = LocalVariableAnalyzer(self.module, self.class_name, self.function_name)
                self.local_variables = analyzer.get_local_variables()

            # Extract conditions from the if statements
            self._extract_conditions(node)
            # Create the helper function
            if self.conditions and self.return_value:
                self._create_helper_function(node)
        return True

    def _extract_conditions(self, func_def: cst.FunctionDef) -> None:
        """Extract conditions from if statements that return the same value.

        Args:
            func_def: The function definition to analyze
        """
        if not isinstance(func_def.body, cst.IndentedBlock):
            return

        # Find consecutive if statements with the same return value within the line range
        for stmt in func_def.body.body:
            if isinstance(stmt, cst.If):
                # Check if this if is within the target line range
                pos = self.get_metadata(cst.metadata.PositionProvider, stmt)
                if not pos or pos.start.line < self.start_line or pos.start.line > self.end_line:
                    continue

                # Check if this if has a simple return in its body
                return_val = self._get_return_value(stmt)
                if return_val is not None:
                    # Check if this is the same as our tracked return value
                    if self.return_value is None:
                        self.return_value = return_val
                        self.conditions.append(stmt.test)
                        self.num_ifs_to_replace = 1
                        # Collect variables used in this condition
                        collector = VariableUsageCollector()
                        stmt.test.visit(collector)
                        self._add_variables(collector.used_variables)
                    elif self._are_equal_values(return_val, self.return_value):
                        # Same return value, add this condition
                        self.conditions.append(stmt.test)
                        self.num_ifs_to_replace += 1
                        # Collect variables used in this condition
                        collector = VariableUsageCollector()
                        stmt.test.visit(collector)
                        self._add_variables(collector.used_variables)
                    else:
                        # Different return value, stop looking
                        break
                else:
                    # Not a simple return, stop looking
                    if self.conditions:
                        break

    def _add_variables(self, variables: list[str]) -> None:
        """Add variables to the list of variables used in conditions.

        Args:
            variables: List of variable names to add
        """
        for var in variables:
            if var not in self.variables_used_in_conditions:
                self.variables_used_in_conditions.append(var)

    def _get_return_value(self, if_stmt: cst.If) -> cst.BaseExpression | None:
        """Get the return value from an if statement if it has a simple return.

        Args:
            if_stmt: The if statement to check

        Returns:
            The return value expression, or None if not a simple return
        """
        if not isinstance(if_stmt.body, cst.IndentedBlock):
            return None

        if len(if_stmt.body.body) != 1:
            return None

        body_stmt = if_stmt.body.body[0]
        if not isinstance(body_stmt, cst.SimpleStatementLine):
            return None

        if len(body_stmt.body) != 1:
            return None

        item = body_stmt.body[0]
        if isinstance(item, cst.Return) and item.value:
            return item.value

        return None

    def _are_equal_values(self, val1: cst.BaseExpression, val2: cst.BaseExpression) -> bool:
        """Check if two values are equal.

        Args:
            val1: First value
            val2: Second value

        Returns:
            True if values are equal
        """
        # Currently only supports integer comparison for the simple case
        # This is sufficient for the most common scenario where multiple
        # conditions return the same constant (e.g., return 0)
        if isinstance(val1, cst.Integer) and isinstance(val2, cst.Integer):
            return val1.value == val2.value
        return False

    def _get_first_parameter(self, func_def: cst.FunctionDef) -> cst.Param | None:
        """Get the first parameter from a function definition.

        Args:
            func_def: The function definition

        Returns:
            The first parameter, or None if no parameters
        """
        if isinstance(func_def.params, cst.Parameters):
            if len(func_def.params.params) > 0:
                return func_def.params.params[0]
        return None

    def _create_helper_function(self, func_def: cst.FunctionDef) -> None:
        """Create the helper function with consolidated conditions.

        Args:
            func_def: The original function definition
        """
        # For methods, we only need self (first_param)
        # For functions, we need at least one parameter
        if not self._is_method and self._first_param is None:
            return

        # Combine conditions with 'or'
        combined_condition = self.conditions[0]
        for condition in self.conditions[1:]:
            combined_condition = cst.BooleanOperation(
                left=combined_condition, operator=cst.Or(), right=condition
            )

        # Create return statement
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=combined_condition)])

        # Build parameters: start with regular params, then add all variables used in conditions
        all_params: list[cst.Param] = []

        if self._is_method:
            all_params.append(create_parameter("self"))
            if self._second_param:
                all_params.append(self._second_param)
        elif self._first_param:
            all_params.append(self._first_param)

        # Add variables used in conditions (local vars and other function params)
        for var in self.variables_used_in_conditions:
            # Check if this variable is already added as a param
            param_names = [p.name.value for p in all_params]
            if var not in param_names:
                all_params.append(create_parameter(var))

        # Create helper function
        self.helper_function = cst.FunctionDef(
            name=cst.Name(self.helper_name),
            params=cst.Parameters(params=all_params),
            body=cst.IndentedBlock(body=[return_stmt]),
        )

    def _build_consolidated_if_statement(self, func_def: cst.FunctionDef) -> cst.If | None:
        """Build the consolidated if statement that calls the helper function.

        Args:
            func_def: The function definition being transformed

        Returns:
            The consolidated if statement, or None if it cannot be built
        """
        if self.return_value is None:
            return None

        # Create call to helper function
        if self._is_method:
            helper_func: cst.BaseExpression = cst.Attribute(
                value=cst.Name("self"),
                attr=cst.Name(self.helper_name),
            )
        else:
            helper_func = cst.Name(self.helper_name)

        # Build arguments for the helper call
        args: list[cst.Arg] = []

        # For methods with only self (e.g., @property), don't pass any arguments
        # For methods with additional params, pass those params
        # For functions, pass the first parameter
        if self._is_method:
            if self._second_param:
                args.append(cst.Arg(value=self._second_param.name))
        else:
            if self._first_param:
                args.append(cst.Arg(value=self._first_param.name))

        # Add any additional variables used in conditions
        for var in self.variables_used_in_conditions:
            # Skip if it's already added as an arg
            arg_names = [arg.value.value for arg in args if isinstance(arg.value, cst.Name)]
            if var not in arg_names:
                args.append(cst.Arg(value=cst.Name(var)))

        helper_call = cst.Call(func=helper_func, args=args)

        # Create return statement with the consolidated return value
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=self.return_value)])

        # Create the if statement
        return cst.If(test=helper_call, body=cst.IndentedBlock(body=[return_stmt]))

    def _should_replace_if_statement(self, if_stmt: cst.If) -> bool:
        """Check if an if statement should be replaced as part of consolidation.

        Args:
            if_stmt: The if statement to check

        Returns:
            True if this if statement matches the consolidation criteria
        """
        if self.return_value is None:
            return False

        return_val = self._get_return_value(if_stmt)
        return return_val is not None and self._are_equal_values(return_val, self.return_value)

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and replace if statements with consolidated version."""
        if original_node.name.value != self.function_name:
            return updated_node

        if not isinstance(updated_node.body, cst.IndentedBlock):
            return updated_node

        # Replace the if statements with a single consolidated if
        new_body: list[cst.BaseStatement] = []
        if_count = 0

        for stmt in updated_node.body.body:
            # Count consecutive if statements at the start
            if isinstance(stmt, cst.If) and self._should_replace_if_statement(stmt):
                if_count += 1

                # Only replace on the first matching if
                if if_count == 1:
                    consolidated_if = self._build_consolidated_if_statement(updated_node)
                    if consolidated_if:
                        new_body.append(consolidated_if)

                # Skip all ifs that should be replaced
                if if_count <= self.num_ifs_to_replace:
                    continue

            new_body.append(stmt)

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class and add helper function if it's a class method."""
        # Only add helper in the class if this is a class method
        # Skip if this is just tracking exit from class (checked below)
        if original_node.name.value != self.class_name:
            return updated_node

        if not self._is_method or not self.helper_function:
            # This is just exiting the tracked class, not adding a helper
            # Handle the first leave_ClassDef logic
            self.current_class = None
            return updated_node

        if not isinstance(updated_node.body, cst.IndentedBlock):
            return updated_node

        # Add helper function after the original method
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body.body:
            new_body.append(stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.function_name:
                # Add helper function with proper spacing
                helper_with_leading_lines = self.helper_function.with_changes(
                    leading_lines=[
                        cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                        cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                    ]
                )
                new_body.append(helper_with_leading_lines)

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and add helper function for module-level functions."""
        # Only add helper at module level if this is NOT a class method
        if self._is_method or not self.helper_function:
            return updated_node

        # Add helper function after the original function
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            new_body.append(stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.function_name:
                # Add helper function with proper spacing
                helper_with_leading_lines = self.helper_function.with_changes(
                    leading_lines=[
                        cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                        cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                    ]
                )
                new_body.append(helper_with_leading_lines)

        return updated_node.with_changes(body=new_body)


class VariableUsageCollector(cst.CSTVisitor):
    """Collector for all variable references in code."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.used_variables: list[str] = []

    def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802
        """Collect variable names used in expressions."""
        var_name = node.value
        # Skip Python keywords and builtins
        if var_name not in self.used_variables and not self._is_builtin(var_name):
            self.used_variables.append(var_name)
        return True

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # noqa: N802
        """Visit attribute, but only process the base value."""
        # Only visit the base value, not the attribute name
        node.value.visit(self)
        # Return False to prevent visiting the attribute name
        return False

    @staticmethod
    def _is_builtin(name: str) -> bool:
        """Check if a name is a Python builtin or keyword.

        Args:
            name: Variable name to check

        Returns:
            True if it's a builtin/keyword, False otherwise
        """
        builtins = {
            "True",
            "False",
            "None",
            "self",
            "cls",
            "Exception",
            "ValueError",
            "TypeError",
            "AttributeError",
        }
        return name in builtins


# Register the command
register_command(ConsolidateConditionalExpressionCommand)
