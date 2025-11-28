"""Decompose Conditional refactoring command."""

from typing import Any

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_range, parse_target
from molting.core.code_generation_utils import create_parameter


class DecomposeConditionalCommand(BaseCommand):
    """Command to extract conditional logic into separate methods."""

    name = "decompose-conditional"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def _parse_target_and_lines(self, target: str) -> tuple[str | None, str, int, int]:
        """Parse target format into class name, function name, and line range.

        Args:
            target: Target string in format:
                - "function_name#L2-L5"
                - "ClassName::function_name#L2-L5"

        Returns:
            Tuple of (class_name or None, function_name, start_line, end_line)

        Raises:
            ValueError: If target format is invalid
        """
        parts = target.split("#")
        if len(parts) != 2:
            raise ValueError(f"Invalid target format '{target}'. Expected 'function_name#L2-L5' or 'ClassName::function_name#L2-L5'")

        path_part = parts[0]
        line_range = parts[1]

        start_line, end_line = parse_line_range(line_range)

        # Parse the path part (class_name::function_name or just function_name)
        if "::" in path_part:
            class_name, function_name = parse_target(path_part, expected_parts=2)
            return class_name, function_name, start_line, end_line
        else:
            return None, path_part, start_line, end_line

    def execute(self) -> None:
        """Apply decompose-conditional refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]
        class_name, function_name, start_line, end_line = self._parse_target_and_lines(target)

        # Read file
        source_code = self.file_path.read_text()

        # Parse and transform with metadata
        module = cst.parse_module(source_code)
        wrapper = metadata.MetadataWrapper(module)
        transformer = DecomposeConditionalTransformer(class_name, function_name, start_line, end_line)
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class DecomposeConditionalTransformer(cst.CSTTransformer):
    """Transformer to decompose conditional into separate methods."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_name: str | None, function_name: str, start_line: int, end_line: int) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the function (or None if top-level)
            function_name: Name of the function containing the conditional
            start_line: Start line of the conditional
            end_line: End line of the conditional
        """
        self.class_name = class_name
        self.function_name = function_name
        self.start_line = start_line
        self.end_line = end_line
        self.condition_expr: cst.BaseExpression | None = None
        self.then_body: cst.BaseStatement | None = None
        self.else_body: cst.BaseStatement | None = None
        self.condition_params: list[str] = []
        self.then_params: list[str] = []
        self.else_params: list[str] = []
        self.new_functions: list[cst.FunctionDef] = []
        self.current_function: str | None = None
        self.current_class: str | None = None
        self.function_params: list[str] = []
        self.assignment_target: str = ""
        self.is_target_matched = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track current class being visited."""
        self.current_class = node.name.value

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition."""
        self.current_class = None
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track current function being visited."""
        self.current_function = node.name.value
        if self.current_function == self.function_name:
            # Check if this is the target function
            if self.class_name is not None:
                if self.current_class == self.class_name:
                    self.is_target_matched = True
            else:
                # If no class specified, match any function with this name
                self.is_target_matched = True

            if self.is_target_matched:
                # Collect function parameter names
                for param in node.params.params:
                    self.function_params.append(param.name.value)

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef | cst.FlattenSentinel[cst.FunctionDef]:
        """Process function definition after visiting."""
        if self.is_target_matched:
            # Return the updated function along with new helper functions
            if self.new_functions:
                return cst.FlattenSentinel([updated_node] + self.new_functions)
            self.is_target_matched = False

        self.current_function = None
        return updated_node

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> Any:  # noqa: N802
        """Transform if statement by decomposing conditional."""
        if not self.is_target_matched or self.current_function != self.function_name:
            return updated_node

        # Check if this if statement is in the target line range
        pos = self.get_metadata(cst.metadata.PositionProvider, original_node)
        if not pos:
            return updated_node

        if pos.start.line != self.start_line:
            return updated_node

        # Extract the condition
        self.condition_expr = original_node.test

        # Extract parameters used in condition
        condition_visitor = ParameterCollector(self.function_params)
        original_node.test.visit(condition_visitor)
        self.condition_params = condition_visitor.params

        # Extract then body
        if original_node.body and original_node.body.body:
            then_stmt = original_node.body.body[0]
            if isinstance(then_stmt, cst.BaseStatement):
                self.then_body = then_stmt
                then_visitor = ParameterCollector(self.function_params)
                self.then_body.visit(then_visitor)
                self.then_params = then_visitor.params
                # Extract assignment target name
                if not self.assignment_target:
                    self.assignment_target = self._extract_assignment_target(self.then_body)

        # Extract else body
        if original_node.orelse and isinstance(original_node.orelse, cst.Else):
            if original_node.orelse.body and original_node.orelse.body.body:
                else_stmt = original_node.orelse.body.body[0]
                if isinstance(else_stmt, cst.BaseStatement):
                    self.else_body = else_stmt
                    else_visitor = ParameterCollector(self.function_params)
                    self.else_body.visit(else_visitor)
                    self.else_params = else_visitor.params

        # Create new functions
        self._create_helper_functions()

        # Replace the if statement with calls to the new functions
        return self._create_replacement_if()

    def _create_helper_functions(self) -> None:
        """Create helper functions for condition, then, and else branches."""
        if self.condition_expr and self.condition_params:
            condition_func = self._create_function(
                "is_winter", self.condition_params, self.condition_expr
            )
            self.new_functions.append(condition_func)

        if self.then_body and self.then_params:
            then_value = self._extract_return_value(self.then_body)
            if then_value:
                then_func = self._create_function("winter_charge", self.then_params, then_value)
                self.new_functions.append(then_func)

        if self.else_body and self.else_params:
            else_value = self._extract_return_value(self.else_body)
            if else_value:
                else_func = self._create_function("summer_charge", self.else_params, else_value)
                self.new_functions.append(else_func)

    def _create_function(
        self, name: str, params: list[str], return_value: cst.BaseExpression
    ) -> cst.FunctionDef:
        """Create a function definition with given name, parameters, and return value.

        Args:
            name: Name of the function
            params: List of parameter names
            return_value: Expression to return

        Returns:
            Function definition node
        """
        return cst.FunctionDef(
            name=cst.Name(name),
            params=cst.Parameters(params=[create_parameter(param) for param in params]),
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
        """Create replacement if statement using the new functions."""
        # Create call to is_winter(date)
        condition_call = cst.Call(
            func=cst.Name("is_winter"),
            args=[cst.Arg(value=cst.Name(param)) for param in self.condition_params],
        )

        # Create call to winter_charge(...)
        then_call = cst.Call(
            func=cst.Name("winter_charge"),
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

        # Create call to summer_charge(...)
        else_call = cst.Call(
            func=cst.Name("summer_charge"),
            args=[cst.Arg(value=cst.Name(param)) for param in self.else_params],
        )
        else_assign = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.assignment_target))],
                    value=else_call,
                )
            ]
        )

        # Create new if statement
        return cst.If(
            test=condition_call,
            body=cst.IndentedBlock(body=[then_assign]),
            orelse=cst.Else(body=cst.IndentedBlock(body=[else_assign])),
        )


class ParameterCollector(cst.CSTVisitor):
    """Visitor to collect parameter names used in expressions."""

    def __init__(self, valid_params: list[str]) -> None:
        """Initialize the collector.

        Args:
            valid_params: List of valid function parameter names to collect
        """
        self.valid_params = set(valid_params)
        self.params: list[str] = []

    def visit_Name(self, node: cst.Name) -> None:  # noqa: N802
        """Collect name references that are valid parameters."""
        if node.value in self.valid_params and node.value not in self.params:
            self.params.append(node.value)


# Register the command
register_command(DecomposeConditionalCommand)
