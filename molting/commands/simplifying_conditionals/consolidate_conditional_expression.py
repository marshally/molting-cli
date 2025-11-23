"""Consolidate Conditional Expression refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ConsolidateConditionalExpressionCommand(BaseCommand):
    """Command to consolidate multiple conditionals with the same result."""

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

        # Parse target format: "function_name#L2-L7"
        if "#L" not in target:
            raise ValueError(f"Invalid target format '{target}'. Expected 'function_name#L2-L7'")

        parts = target.split("#L")
        function_name = parts[0]

        # Apply transformation
        self.apply_libcst_transform(
            ConsolidateConditionalExpressionTransformer,
            function_name,
            helper_name,
        )


class ConsolidateConditionalExpressionTransformer(cst.CSTTransformer):
    """Transforms sequential if statements into a consolidated conditional."""

    def __init__(self, function_name: str, helper_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to refactor
            helper_name: Name of the helper function to create
        """
        self.function_name = function_name
        self.helper_name = helper_name
        self.conditions: list[cst.BaseExpression] = []
        self.return_value: cst.BaseExpression | None = None
        self.helper_function: cst.FunctionDef | None = None
        self.num_ifs_to_replace = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to find target function."""
        if node.name.value == self.function_name:
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

        # Find consecutive if statements with the same return value
        for stmt in func_def.body.body:
            if isinstance(stmt, cst.If):
                # Check if this if has a simple return in its body
                return_val = self._get_return_value(stmt)
                if return_val is not None:
                    # Check if this is the same as our tracked return value
                    if self.return_value is None:
                        self.return_value = return_val
                        self.conditions.append(stmt.test)
                        self.num_ifs_to_replace = 1
                    elif self._are_equal_values(return_val, self.return_value):
                        # Same return value, add this condition
                        self.conditions.append(stmt.test)
                        self.num_ifs_to_replace += 1
                    else:
                        # Different return value, stop looking
                        break
                else:
                    # Not a simple return, stop looking
                    if self.conditions:
                        break

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
        param = self._get_first_parameter(func_def)
        if param is None:
            return

        # Combine conditions with 'or'
        combined_condition = self.conditions[0]
        for condition in self.conditions[1:]:
            combined_condition = cst.BooleanOperation(
                left=combined_condition, operator=cst.Or(), right=condition
            )

        # Create return statement
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=combined_condition)])

        # Create helper function
        self.helper_function = cst.FunctionDef(
            name=cst.Name(self.helper_name),
            params=cst.Parameters(params=[param]),
            body=cst.IndentedBlock(body=[return_stmt]),
        )

    def _build_consolidated_if_statement(self, func_def: cst.FunctionDef) -> cst.If | None:
        """Build the consolidated if statement that calls the helper function.

        Args:
            func_def: The function definition being transformed

        Returns:
            The consolidated if statement, or None if it cannot be built
        """
        param = self._get_first_parameter(func_def)
        if param is None or self.return_value is None:
            return None

        # Create call to helper function
        helper_call = cst.Call(func=cst.Name(self.helper_name), args=[cst.Arg(value=param.name)])

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

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and add helper function."""
        if not self.helper_function:
            return updated_node

        # Add helper function after the original function
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            new_body.append(stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.function_name:
                # Add empty lines and helper function
                new_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                new_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                new_body.append(self.helper_function)

        return updated_node.with_changes(body=new_body)


# Register the command
register_command(ConsolidateConditionalExpressionCommand)
