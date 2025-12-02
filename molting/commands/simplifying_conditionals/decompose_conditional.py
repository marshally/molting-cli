"""Decompose Conditional refactoring command."""

from dataclasses import dataclass
from typing import Any

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_range
from molting.core.code_generation_utils import create_parameter
from molting.core.conditional_pattern import build_param_map, normalize_condition
from molting.core.local_variable_analyzer import LocalVariableAnalyzer


@dataclass
class DecomposePatternMatch:
    """Represents a function that matches a decompose conditional pattern."""

    function_name: str
    class_name: str
    start_line: int
    assignment_target: str


class DecomposeConditionalCommand(BaseCommand):
    """Decompose Conditional refactoring: extract complex conditional logic into named methods.

    This refactoring extracts the condition, then-branch, and else-branch of a complicated
    conditional statement into separate, well-named helper methods. By breaking down the
    conditional logic into discrete methods with clear names, the original code becomes
    more readable and the intent becomes explicit.

    **When to use:**
    - When a conditional statement is difficult to understand at a glance
    - When the condition itself is complex and would benefit from a named method
    - When the then/else branches perform substantial operations
    - When the same conditions or branches appear in multiple places
    - When you want to make the business logic clearer through method naming

    **Example:**
    Before:
        def charge_for_order(customer):
            if customer.age > 60 and customer.is_resident:
                charge = customer.base_charge * 0.9
            else:
                charge = customer.base_charge * 1.1
            return charge

    After:
        def charge_for_order(customer):
            if is_senior_resident(customer):
                charge = senior_discount(customer)
            else:
                charge = standard_surcharge(customer)
            return charge

        def is_senior_resident(customer):
            return customer.age > 60 and customer.is_resident

        def senior_discount(customer):
            return customer.base_charge * 0.9

        def standard_surcharge(customer):
            return customer.base_charge * 1.1
    """

    name = "decompose-conditional"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "condition_name", "then_name", "else_name")

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

    def execute(self) -> None:
        """Apply decompose-conditional refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]
        condition_name = self.params["condition_name"]
        then_name = self.params["then_name"]
        else_name = self.params["else_name"]
        class_name, function_name, start_line, end_line = self._parse_target(target)

        # Read file
        source_code = self.file_path.read_text()

        # Parse module
        module = cst.parse_module(source_code)

        # Extract pattern from target function and scan for matches
        pattern = extract_decompose_pattern(module, function_name, class_name, start_line)
        additional_matches: list[DecomposePatternMatch] = []
        if pattern:
            additional_matches = scan_for_decompose_pattern(
                module, pattern, function_name, class_name
            )

        # Transform with metadata
        wrapper = metadata.MetadataWrapper(module)
        transformer = DecomposeConditionalTransformer(
            class_name,
            function_name,
            start_line,
            end_line,
            module,
            condition_name=condition_name,
            then_name=then_name,
            else_name=else_name,
            additional_matches=additional_matches,
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class DecomposeConditionalTransformer(cst.CSTTransformer):
    """Transformer to decompose conditional into separate methods."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        class_name: str,
        function_name: str,
        start_line: int,
        end_line: int,
        module: cst.Module | None = None,
        *,
        condition_name: str,
        then_name: str,
        else_name: str,
        additional_matches: list["DecomposePatternMatch"] | None = None,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class (empty string for module-level functions)
            function_name: Name of the function containing the conditional
            start_line: Start line of the conditional
            end_line: End line of the conditional
            module: The CST module for analyzing local variables
            condition_name: Name for the extracted condition function
            then_name: Name for the extracted then-branch function
            else_name: Name for the extracted else-branch function
            additional_matches: List of other functions with matching pattern
        """
        self.class_name = class_name
        self.function_name = function_name
        self.start_line = start_line
        self.end_line = end_line
        self.module = module
        self.condition_name = condition_name
        self.then_name = then_name
        self.else_name = else_name
        self.additional_matches = additional_matches or []
        self.condition_expr: cst.BaseExpression | None = None
        self.then_body: cst.BaseStatement | None = None
        self.else_body: cst.BaseStatement | None = None
        self.then_body_index: int = -1  # Index of the extracted statement in then block
        self.else_body_index: int = -1  # Index of the extracted statement in else block
        self.original_if: cst.If | None = None  # Original if statement
        self.condition_params: list[str] = []
        self.then_params: list[str] = []
        self.else_params: list[str] = []
        self.local_variables: list[str] = []
        self.new_functions: list[cst.FunctionDef] = []
        self.current_function: str | None = None
        self.current_class: str | None = None
        self.function_params: list[str] = []
        self.assignment_target: str = ""
        self._is_method = False
        self._self_references: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track current class being visited."""
        if node.name.value == self.class_name:
            self.current_class = self.class_name
        return True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Track exit from class."""
        if original_node.name.value == self.class_name:
            self.current_class = None
        return updated_node

    def _is_target_function(self) -> bool:
        """Check if current function is the target."""
        if self.current_function != self.function_name:
            return False
        if self.class_name and self.current_class != self.class_name:
            return False
        if not self.class_name and self.current_class:
            return False
        return True

    def _get_match_for_current_function(self) -> DecomposePatternMatch | None:
        """Get the match info for current function if it's an additional match."""
        for match in self.additional_matches:
            if match.function_name == self.current_function:
                if match.class_name == (self.current_class or ""):
                    return match
        return None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track current function being visited."""
        self.current_function = node.name.value

        # Reset per-function state
        self.function_params = []

        if self._is_target_function():
            # Check if this is a class method
            if self.class_name and self.current_class == self.class_name:
                self._is_method = True
            elif not self.class_name:
                self._is_method = False

            # Collect function parameter names
            for param in node.params.params:
                self.function_params.append(param.name.value)

            # Analyze local variables early so they're available in leave_If
            if self.module and not self.local_variables:
                analyzer = LocalVariableAnalyzer(self.module, self.class_name, self.function_name)
                self.local_variables = analyzer.get_local_variables()
        elif self._get_match_for_current_function():
            # For additional matches, collect function parameters
            for param in node.params.params:
                self.function_params.append(param.name.value)

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef | cst.FlattenSentinel[cst.FunctionDef]:
        """Process function definition after visiting."""
        # For class methods, add helper functions after the method
        if self._is_target_function() and self._is_method and self.new_functions:
            result = cst.FlattenSentinel([updated_node] + self.new_functions)
            self.new_functions = []  # Clear so leave_Module doesn't add them again
            self.current_function = None
            return result

        self.current_function = None
        return updated_node

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> Any:  # noqa: N802
        """Transform if statement by decomposing conditional."""
        pos = self.get_metadata(cst.metadata.PositionProvider, original_node)
        if not pos:
            return updated_node

        # Check if this is the target function at the target line
        if self._is_target_function() and pos.start.line == self.start_line:
            return self._process_target_if(original_node)

        # Check if this is an additional match
        match = self._get_match_for_current_function()
        if match and pos.start.line == match.start_line:
            return self._process_matched_if(original_node, match)

        return updated_node

    def _process_target_if(self, original_node: cst.If) -> cst.If:
        """Process the target if statement and extract patterns."""
        # Store the original if statement for later reconstruction
        self.original_if = original_node

        # Extract the condition
        self.condition_expr = original_node.test

        # Extract parameters used in condition (exclude 'self' for methods)
        # Include both function parameters and local variables
        params_to_collect = [p for p in self.function_params if p != "self"]
        params_to_collect.extend(self.local_variables)
        condition_visitor = ParameterCollector(params_to_collect)
        original_node.test.visit(condition_visitor)
        self.condition_params = condition_visitor.params

        # Extract then body (use last statement to handle multiple statements in branch)
        if original_node.body and original_node.body.body:
            # Track which statement index we're extracting (the last one)
            self.then_body_index = len(original_node.body.body) - 1
            then_stmt = original_node.body.body[self.then_body_index]
            if isinstance(then_stmt, cst.BaseStatement):
                self.then_body = then_stmt
                then_visitor = ParameterCollector(params_to_collect)
                self.then_body.visit(then_visitor)
                self.then_params = then_visitor.params
                # Extract assignment target name
                if not self.assignment_target:
                    self.assignment_target = self._extract_assignment_target(self.then_body)

        # Extract else body (use last statement to handle multiple statements in branch)
        if original_node.orelse and isinstance(original_node.orelse, cst.Else):
            if original_node.orelse.body and original_node.orelse.body.body:
                # Track which statement index we're extracting (the last one)
                self.else_body_index = len(original_node.orelse.body.body) - 1
                else_stmt = original_node.orelse.body.body[self.else_body_index]
                if isinstance(else_stmt, cst.BaseStatement):
                    self.else_body = else_stmt
                    else_visitor = ParameterCollector(params_to_collect)
                    self.else_body.visit(else_visitor)
                    self.else_params = else_visitor.params

        # Create new functions
        self._create_helper_functions()

        # Replace the if statement with calls to the new functions
        return self._create_replacement_if()

    def _process_matched_if(self, original_node: cst.If, match: DecomposePatternMatch) -> cst.If:
        """Process an if statement in a matched function."""
        # For matched functions, we use the same helpers but with the match's assignment target
        # The helper functions and params are already extracted from the target
        return self._create_replacement_if_for_match(original_node, match)

    def _create_helper_functions(self) -> None:
        """Create helper functions for condition, then, and else branches.

        For methods that use only self attributes (no local variables or function params),
        the params list will be empty but we still need to create the helper methods.
        """
        # For methods, we can have empty params if only self attributes are used
        # For functions, we need at least some params to pass values
        can_have_empty_params = self._is_method

        if self.condition_expr and (self.condition_params or can_have_empty_params):
            condition_func = self._create_function(
                self.condition_name, self.condition_params, self.condition_expr
            )
            self.new_functions.append(condition_func)

        if self.then_body and (self.then_params or can_have_empty_params):
            then_value = self._extract_return_value(self.then_body)
            if then_value:
                then_func = self._create_function(self.then_name, self.then_params, then_value)
                self.new_functions.append(then_func)

        if self.else_body and (self.else_params or can_have_empty_params):
            else_value = self._extract_return_value(self.else_body)
            if else_value:
                else_func = self._create_function(self.else_name, self.else_params, else_value)
                self.new_functions.append(else_func)

    def _create_function(
        self, name: str, params: list[str], return_value: cst.BaseExpression
    ) -> cst.FunctionDef:
        """Create a function definition with given name, parameters, and return value.

        Args:
            name: Name of the function
            params: List of parameter names (not including 'self')
            return_value: Expression to return

        Returns:
            Function definition node
        """
        # If this is a method, add 'self' as the first parameter
        all_params = params
        if self._is_method:
            all_params = ["self"] + params

        return cst.FunctionDef(
            name=cst.Name(name),
            params=cst.Parameters(params=[create_parameter(param) for param in all_params]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[cst.Return(value=return_value)],
                    )
                ]
            ),
        )

    def _extract_return_value(self, stmt: cst.BaseStatement) -> cst.BaseExpression | None:
        """Extract the assigned value from an assignment statement."""
        if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) > 0:
            first_stmt = stmt.body[0]
            if isinstance(first_stmt, cst.Assign) and len(first_stmt.targets) > 0:
                return first_stmt.value
        return None

    def _extract_assignment_target(self, stmt: cst.BaseStatement) -> str:
        """Extract the target variable name from an assignment statement."""
        if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) > 0:
            first_stmt = stmt.body[0]
            if isinstance(first_stmt, cst.Assign) and len(first_stmt.targets) > 0:
                target = first_stmt.targets[0].target
                if isinstance(target, cst.Name):
                    return target.value
        return ""

    def _create_replacement_if(self) -> cst.If:
        """Create replacement if using new functions, preserving other statements."""
        if not self.original_if:
            return cst.If(test=cst.Name("False"), body=cst.IndentedBlock(body=[]))

        # Create call to condition function
        if self._is_method:
            condition_func: cst.BaseExpression = cst.Attribute(
                value=cst.Name("self"),
                attr=cst.Name(self.condition_name),
            )
        else:
            condition_func = cst.Name(self.condition_name)

        condition_call = cst.Call(
            func=condition_func,
            args=[cst.Arg(value=cst.Name(param)) for param in self.condition_params],
        )

        # Build the then block with all statements, replacing the extracted one
        then_statements: list[cst.BaseStatement] = []
        if self.original_if.body and self.original_if.body.body:
            for i, stmt in enumerate(self.original_if.body.body):
                if i == self.then_body_index:
                    # Replace with extracted function call
                    if self._is_method:
                        then_func: cst.BaseExpression = cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name(self.then_name),
                        )
                    else:
                        then_func = cst.Name(self.then_name)

                    then_call = cst.Call(
                        func=then_func,
                        args=[cst.Arg(value=cst.Name(param)) for param in self.then_params],
                    )
                    then_assign = cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[cst.AssignTarget(target=cst.Name(self.assignment_target))],
                                value=then_call,
                            )
                        ]
                    )
                    then_statements.append(then_assign)
                else:
                    # Keep original statement
                    then_statements.append(stmt)  # type: ignore[arg-type]

        # Build the else block with all statements, replacing the extracted one
        else_statements: list[cst.BaseStatement] = []
        if self.original_if.orelse and isinstance(self.original_if.orelse, cst.Else):
            if self.original_if.orelse.body and self.original_if.orelse.body.body:
                for i, stmt in enumerate(self.original_if.orelse.body.body):
                    if i == self.else_body_index:
                        # Replace with extracted function call
                        if self._is_method:
                            else_func: cst.BaseExpression = cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(self.else_name),
                            )
                        else:
                            else_func = cst.Name(self.else_name)

                        else_call = cst.Call(
                            func=else_func,
                            args=[cst.Arg(value=cst.Name(param)) for param in self.else_params],
                        )
                        else_assign = cst.SimpleStatementLine(
                            body=[
                                cst.Assign(
                                    targets=[
                                        cst.AssignTarget(target=cst.Name(self.assignment_target))
                                    ],
                                    value=else_call,
                                )
                            ]
                        )
                        else_statements.append(else_assign)
                    else:
                        # Keep original statement
                        else_statements.append(stmt)  # type: ignore[arg-type]

        # Create new if statement
        else_clause = None
        if else_statements:
            else_clause = cst.Else(body=cst.IndentedBlock(body=else_statements))

        return cst.If(
            test=condition_call,
            body=cst.IndentedBlock(body=then_statements),
            orelse=else_clause,
        )

    def _create_replacement_if_for_match(
        self, original_if: cst.If, match: DecomposePatternMatch
    ) -> cst.If:
        """Create replacement if for a matched function using existing helper functions."""
        # Create call to condition function
        condition_func: cst.BaseExpression = cst.Name(self.condition_name)
        condition_call = cst.Call(
            func=condition_func,
            args=[cst.Arg(value=cst.Name(param)) for param in self.condition_params],
        )

        # Build the then block - find and replace the assignment statement
        then_statements: list[cst.BaseStatement] = []
        if original_if.body and original_if.body.body:
            for i, stmt in enumerate(original_if.body.body):
                # Replace the last statement (the assignment) with a call
                if i == len(original_if.body.body) - 1:
                    then_func: cst.BaseExpression = cst.Name(self.then_name)
                    then_call = cst.Call(
                        func=then_func,
                        args=[cst.Arg(value=cst.Name(param)) for param in self.then_params],
                    )
                    then_assign = cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(target=cst.Name(match.assignment_target))
                                ],
                                value=then_call,
                            )
                        ]
                    )
                    then_statements.append(then_assign)
                else:
                    then_statements.append(stmt)  # type: ignore[arg-type]

        # Build the else block
        else_statements: list[cst.BaseStatement] = []
        if original_if.orelse and isinstance(original_if.orelse, cst.Else):
            if original_if.orelse.body and original_if.orelse.body.body:
                for i, stmt in enumerate(original_if.orelse.body.body):
                    if i == len(original_if.orelse.body.body) - 1:
                        else_func: cst.BaseExpression = cst.Name(self.else_name)
                        else_call = cst.Call(
                            func=else_func,
                            args=[cst.Arg(value=cst.Name(param)) for param in self.else_params],
                        )
                        else_assign = cst.SimpleStatementLine(
                            body=[
                                cst.Assign(
                                    targets=[
                                        cst.AssignTarget(target=cst.Name(match.assignment_target))
                                    ],
                                    value=else_call,
                                )
                            ]
                        )
                        else_statements.append(else_assign)
                    else:
                        else_statements.append(stmt)  # type: ignore[arg-type]

        else_clause = None
        if else_statements:
            else_clause = cst.Else(body=cst.IndentedBlock(body=else_statements))

        return cst.If(
            test=condition_call,
            body=cst.IndentedBlock(body=then_statements),
            orelse=else_clause,
        )

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add helper functions at the end of the module."""
        if not self.new_functions:
            return updated_node

        # Add helper functions at the end of the module
        new_body = list(updated_node.body) + self.new_functions
        return updated_node.with_changes(body=new_body)


class ParameterCollector(cst.CSTVisitor):
    """Visitor to collect parameter names used in expressions (not assignment targets)."""

    def __init__(self, valid_params: list[str]) -> None:
        """Initialize the collector.

        Args:
            valid_params: List of valid function parameter names to collect
        """
        self.valid_params = set(valid_params)
        self.params: list[str] = []

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Visit assignment, but only process the RHS value, not the targets."""
        # Only visit the RHS (the value being assigned), not the targets
        node.value.visit(self)
        # Return False to prevent visiting the targets
        return False

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # noqa: N802
        """Visit attribute, but only process the base value, not the attribute name."""
        # Only visit the base value, not the attribute name
        node.value.visit(self)
        # Return False to prevent visiting the attribute name
        return False

    def visit_Name(self, node: cst.Name) -> None:  # noqa: N802
        """Collect name references that are valid parameters."""
        if node.value in self.valid_params and node.value not in self.params:
            self.params.append(node.value)


@dataclass(frozen=True)
class DecomposePatternSignature:
    """Hashable representation of a decompose conditional pattern."""

    condition: str  # Normalized condition string
    then_value: str  # Normalized then-branch value
    else_value: str  # Normalized else-branch value


class DecomposePatternExtractor(cst.CSTVisitor):
    """Extracts a decompose conditional pattern from a specific function."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        target_function: str,
        target_class: str,
        start_line: int,
    ) -> None:
        """Initialize the extractor."""
        self.target_function = target_function
        self.target_class = target_class
        self.start_line = start_line
        self.current_class: str = ""
        self.signature: DecomposePatternSignature | None = None
        self.assignment_target: str = ""

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track current class."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Reset class tracking."""
        self.current_class = ""

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Extract pattern from target function."""
        if node.name.value != self.target_function:
            return True
        if self.target_class and self.current_class != self.target_class:
            return True
        if not self.target_class and self.current_class:
            return True

        param_map = build_param_map(node)

        # Find if statement at target line
        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.If):
                    try:
                        pos = self.get_metadata(metadata.PositionProvider, stmt)
                        if pos.start.line != self.start_line:
                            continue
                    except KeyError:
                        continue

                    # Extract and normalize condition
                    condition = normalize_condition(stmt.test, param_map)

                    # Extract then value
                    then_value = ""
                    if stmt.body and stmt.body.body:
                        last_stmt = stmt.body.body[-1]
                        if isinstance(last_stmt, cst.SimpleStatementLine):
                            if last_stmt.body and isinstance(last_stmt.body[0], cst.Assign):
                                assign = last_stmt.body[0]
                                then_value = normalize_condition(assign.value, param_map)
                                # Extract assignment target
                                target = assign.targets[0].target
                                if isinstance(target, cst.Name):
                                    self.assignment_target = target.value

                    # Extract else value
                    else_value = ""
                    if stmt.orelse and isinstance(stmt.orelse, cst.Else):
                        if stmt.orelse.body and stmt.orelse.body.body:
                            last_stmt = stmt.orelse.body.body[-1]
                            if isinstance(last_stmt, cst.SimpleStatementLine):
                                if last_stmt.body and isinstance(last_stmt.body[0], cst.Assign):
                                    assign = last_stmt.body[0]
                                    else_value = normalize_condition(assign.value, param_map)

                    if condition and then_value and else_value:
                        self.signature = DecomposePatternSignature(
                            condition=condition,
                            then_value=then_value,
                            else_value=else_value,
                        )
                    break

        return True


class DecomposePatternScanner(cst.CSTVisitor):
    """Scans a module for functions with matching decompose conditional pattern."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        target_pattern: DecomposePatternSignature,
        exclude_function: str,
        exclude_class: str,
    ) -> None:
        """Initialize the scanner."""
        self.target_pattern = target_pattern
        self.exclude_function = exclude_function
        self.exclude_class = exclude_class
        self.matches: list[DecomposePatternMatch] = []
        self.current_class: str = ""

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track current class."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Reset class tracking."""
        self.current_class = ""

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Check if function matches pattern."""
        # Skip the target function
        if node.name.value == self.exclude_function:
            if not self.exclude_class and not self.current_class:
                return True
            if self.exclude_class == self.current_class:
                return True

        param_map = build_param_map(node)

        # Find first if-else statement
        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.If) and stmt.orelse:
                    try:
                        pos = self.get_metadata(metadata.PositionProvider, stmt)
                        start_line = pos.start.line
                    except KeyError:
                        continue

                    # Extract and normalize condition
                    condition = normalize_condition(stmt.test, param_map)

                    # Extract then value
                    then_value = ""
                    assignment_target = ""
                    if stmt.body and stmt.body.body:
                        last_stmt = stmt.body.body[-1]
                        if isinstance(last_stmt, cst.SimpleStatementLine):
                            if last_stmt.body and isinstance(last_stmt.body[0], cst.Assign):
                                assign = last_stmt.body[0]
                                then_value = normalize_condition(assign.value, param_map)
                                target = assign.targets[0].target
                                if isinstance(target, cst.Name):
                                    assignment_target = target.value

                    # Extract else value
                    else_value = ""
                    if stmt.orelse and isinstance(stmt.orelse, cst.Else):
                        if stmt.orelse.body and stmt.orelse.body.body:
                            last_stmt = stmt.orelse.body.body[-1]
                            if isinstance(last_stmt, cst.SimpleStatementLine):
                                if last_stmt.body and isinstance(last_stmt.body[0], cst.Assign):
                                    assign = last_stmt.body[0]
                                    else_value = normalize_condition(assign.value, param_map)

                    # Check if pattern matches
                    if (
                        condition == self.target_pattern.condition
                        and then_value == self.target_pattern.then_value
                        and else_value == self.target_pattern.else_value
                        and assignment_target
                    ):
                        self.matches.append(
                            DecomposePatternMatch(
                                function_name=node.name.value,
                                class_name=self.current_class,
                                start_line=start_line,
                                assignment_target=assignment_target,
                            )
                        )
                    break

        return True


def extract_decompose_pattern(
    module: cst.Module,
    function_name: str,
    class_name: str,
    start_line: int,
) -> DecomposePatternSignature | None:
    """Extract a decompose conditional pattern from a function."""
    wrapper = metadata.MetadataWrapper(module)
    extractor = DecomposePatternExtractor(function_name, class_name, start_line)
    wrapper.visit(extractor)
    return extractor.signature


def scan_for_decompose_pattern(
    module: cst.Module,
    pattern: DecomposePatternSignature,
    exclude_function: str,
    exclude_class: str,
) -> list[DecomposePatternMatch]:
    """Scan a module for functions matching a decompose pattern."""
    wrapper = metadata.MetadataWrapper(module)
    scanner = DecomposePatternScanner(pattern, exclude_function, exclude_class)
    wrapper.visit(scanner)
    return scanner.matches


# Register the command
register_command(DecomposeConditionalCommand)
