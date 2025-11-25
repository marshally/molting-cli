"""Introduce Explaining Variable refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_number, parse_target_with_line


@register_command
class IntroduceExplainingVariableCommand(BaseCommand):
    """Command to introduce an explaining variable for a complex expression."""

    name = "introduce-explaining-variable"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply introduce-explaining-variable refactoring using libCST.

        Raises:
            ValueError: If function not found or line not found
        """
        target = self.params["target"]
        variable_name = self.params["name"]

        # Parse target format: "function_name#L2"
        function_name, method_name, line_spec = parse_target_with_line(target)
        line_number = parse_line_number(line_spec)

        # If method_name is empty, we're working with a function-level target
        if method_name:
            raise ValueError("Class methods not yet supported, use function-level targets")

        # Read file
        source_code = self.file_path.read_text()

        # First pass: find the target expression
        module = cst.parse_module(source_code)
        wrapper = cst.MetadataWrapper(module)
        finder = ExpressionFinder(function_name, line_number)
        wrapper.visit(finder)

        if finder.target_expression is None:
            raise ValueError(f"No expression found at line {line_number}")

        # Second pass: transform
        transformer = IntroduceExplainingVariableTransformer(
            function_name, finder.target_expression, variable_name
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ExpressionFinder(cst.CSTVisitor):
    """Finds the target expression at a specific line."""

    METADATA_DEPENDENCIES = (cst.metadata.WhitespaceInclusivePositionProvider,)

    def __init__(self, function_name: str, line_number: int) -> None:
        """Initialize the finder.

        Args:
            function_name: Name of the function to search in
            line_number: Line number to find expression at
        """
        self.function_name = function_name
        self.line_number = line_number
        self.target_expression: Any = None
        self.in_target_function = False
        self.smallest_size = float("inf")

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition."""
        if node.name.value == self.function_name:
            self.in_target_function = True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Leave function definition."""
        if node.name.value == self.function_name:
            self.in_target_function = False

    def _check_expression(self, node: cst.BaseExpression) -> None:
        """Check if an expression is at the target line and smaller than current."""
        if not self.in_target_function:
            return

        pos = self.get_metadata(cst.metadata.WhitespaceInclusivePositionProvider, node)
        # Line numbers use 1-based indexing: L2 refers to the second line of the return
        # expression, which is line 3 in the file (def on line 1, return on line 2)
        if pos.start.line == self.line_number + 1:
            # Estimate size
            size = len(cst.Module([]).code_for_node(node))
            if size < self.smallest_size:
                self.smallest_size = size
                self.target_expression = node

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> None:  # noqa: N802
        """Visit binary operation."""
        self._check_expression(node)

    def visit_Call(self, node: cst.Call) -> None:  # noqa: N802
        """Visit call."""
        self._check_expression(node)


class IntroduceExplainingVariableTransformer(cst.CSTTransformer):
    """Transforms a function by introducing an explaining variable."""

    def __init__(self, function_name: str, target_expression: Any, variable_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to refactor
            target_expression: The expression to extract
            variable_name: Name for the new explaining variable
        """
        self.function_name = function_name
        self.target_expression = target_expression
        self.variable_name = variable_name
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition."""
        if node.name.value == self.function_name:
            self.in_target_function = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and introduce the explaining variable."""
        if original_node.name.value != self.function_name:
            return updated_node

        self.in_target_function = False

        assignment = self._create_assignment()
        new_statements = self._insert_before_return(updated_node.body.body, assignment)

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=tuple(new_statements))
        )

    def _create_assignment(self) -> cst.SimpleStatementLine:
        """Create an assignment statement for the extracted variable."""
        return cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.variable_name))],
                    value=self.target_expression,
                )
            ]
        )

    def _insert_before_return(
        self, statements: tuple[cst.BaseStatement, ...], assignment: cst.SimpleStatementLine
    ) -> list[cst.BaseStatement]:
        """Insert assignment statement before the return statement."""
        new_statements = []
        for stmt in statements:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this contains a return statement
                for inner_stmt in stmt.body:
                    if isinstance(inner_stmt, cst.Return):
                        # Insert assignment before return
                        new_statements.append(assignment)
                        break
            new_statements.append(stmt)
        return new_statements

    def _replace_if_target(
        self, original_node: cst.BaseExpression, updated_node: cst.BaseExpression
    ) -> cst.BaseExpression:
        """Replace node with variable name if it's the target expression."""
        if not self.in_target_function:
            return updated_node

        if original_node is self.target_expression:
            return cst.Name(self.variable_name)

        return updated_node

    def leave_BinaryOperation(  # noqa: N802
        self, original_node: cst.BinaryOperation, updated_node: cst.BinaryOperation
    ) -> cst.BaseExpression:
        """Replace target expression with variable name."""
        return self._replace_if_target(original_node, updated_node)

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Replace target expression with variable name."""
        return self._replace_if_target(original_node, updated_node)
