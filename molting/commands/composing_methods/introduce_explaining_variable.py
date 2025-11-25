"""Introduce Explaining Variable refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceExplainingVariableCommand(BaseCommand):
    """Command to introduce an explaining variable for a complex expression."""

    name = "introduce-explaining-variable"

    def validate(self) -> None:
        """Validate that required parameters are present."""
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply introduce-explaining-variable refactoring using libCST.

        Raises:
            ValueError: If target format is invalid or line number is not a positive integer
        """
        target = self.params["target"]
        variable_name = self.params["name"]

        # Parse target: "function_name#L2"
        if "#L" not in target:
            raise ValueError(
                f"Invalid target format '{target}'. Expected format: 'function_name#L<line>'"
            )

        parts = target.split("#L")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid target format '{target}'. Expected format: 'function_name#L<line>'"
            )

        function_name = parts[0]
        if not function_name:
            raise ValueError("Function name cannot be empty")

        try:
            line_number = int(parts[1])
        except ValueError as e:
            raise ValueError(
                f"Invalid line number '{parts[1]}'. Line number must be an integer"
            ) from e

        if line_number < 0:
            raise ValueError(f"Invalid line number {line_number}. Line number must be non-negative")

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = IntroduceVariableTransformer(function_name, variable_name, line_number)
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class IntroduceVariableTransformer(cst.CSTTransformer):
    """Transforms a function by introducing an explaining variable."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, function_name: str, variable_name: str, line_number: int) -> None:
        """Initialize the transformer."""
        self.function_name = function_name
        self.variable_name = variable_name
        self.line_number = line_number
        self.in_target_function = False
        self.target_expression: cst.BaseExpression | None = None
        self.found_return_with_expression = False
        self.candidates: list[tuple[int, cst.BaseExpression]] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to find target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform the function to include the new variable."""
        if original_node.name.value != self.function_name:
            return updated_node

        self.in_target_function = False

        # If we found an expression and transformed the return, add variable assignment
        if self.target_expression and self.found_return_with_expression:
            return self._add_variable_before_return(updated_node)

        return updated_node

    def _add_variable_before_return(self, function_node: cst.FunctionDef) -> cst.FunctionDef:
        """Add a variable assignment before the return statement."""
        if not isinstance(function_node.body, cst.IndentedBlock):
            return function_node

        new_statements: list[cst.BaseStatement] = []
        assignment = self._create_assignment()

        # Insert assignment before the return statement
        for stmt in function_node.body.body:
            if self._is_return_statement(stmt):
                new_statements.append(assignment)
            new_statements.append(stmt)

        return function_node.with_changes(body=cst.IndentedBlock(body=new_statements))

    def _create_assignment(self) -> cst.SimpleStatementLine:
        """Create a variable assignment statement."""
        # target_expression is guaranteed to be set when this method is called
        assert self.target_expression is not None
        return cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.variable_name))],
                    value=self.target_expression,
                )
            ]
        )

    def _is_return_statement(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a return statement."""
        return isinstance(stmt, cst.SimpleStatementLine) and any(
            isinstance(s, cst.Return) for s in stmt.body
        )

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> None:  # noqa: N802
        """Visit binary operations to find target expression."""
        if not self.in_target_function:
            return

        try:
            position = self.get_metadata(metadata.PositionProvider, node)
            # Collect expressions that start at the target line
            if position.start.line == self.line_number + 1:
                self.candidates.append((position.start.line, node))
        except KeyError:
            pass

    def visit_Call(self, node: cst.Call) -> None:  # noqa: N802
        """Visit function calls to find target expression."""
        if not self.in_target_function:
            return

        try:
            position = self.get_metadata(metadata.PositionProvider, node)
            if position.start.line == self.line_number + 1:
                self.candidates.append((position.start.line, node))
        except KeyError:
            pass

    def leave_Return(  # noqa: N802
        self, original_node: cst.Return, updated_node: cst.Return
    ) -> cst.Return:
        """Replace the target expression with the variable name in return statement."""
        if not self.in_target_function or not updated_node.value:
            return updated_node

        # Select the smallest expression from candidates if not yet selected
        if not self.target_expression and self.candidates:
            # Select the smallest expression (most specific)
            self.target_expression = min(
                self.candidates, key=lambda x: len(cst.Module([]).code_for_node(x[1]))
            )[1]

        if not self.target_expression:
            return updated_node

        self.found_return_with_expression = True
        new_value = self._replace_expression(updated_node.value)
        return updated_node.with_changes(value=new_value)

    def _replace_expression(self, node: cst.BaseExpression) -> cst.BaseExpression:
        """Recursively replace the target expression with the variable name."""
        # target_expression is guaranteed to be set when this method is called
        assert self.target_expression is not None
        if node.deep_equals(self.target_expression):
            return cst.Name(self.variable_name)

        # Recursively handle binary operations
        if isinstance(node, cst.BinaryOperation):
            new_left = self._replace_expression(node.left)
            new_right = self._replace_expression(node.right)
            if new_left is not node.left or new_right is not node.right:
                return node.with_changes(left=new_left, right=new_right)

        # Recursively handle function calls
        if isinstance(node, cst.Call):
            new_args = []
            changed = False
            for arg in node.args:
                new_value = self._replace_expression(arg.value)
                if new_value is not arg.value:
                    new_args.append(arg.with_changes(value=new_value))
                    changed = True
                else:
                    new_args.append(arg)
            if changed:
                return node.with_changes(args=new_args)

        return node


# Register the command
register_command(IntroduceExplainingVariableCommand)
