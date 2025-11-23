"""Introduce Assertion refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceAssertionCommand(BaseCommand):
    """Command to make assumptions explicit with an assertion."""

    name = "introduce-assertion"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "condition")

    def execute(self) -> None:
        """Apply introduce-assertion refactoring using libCST.

        Raises:
            ValueError: If target format is invalid
        """
        target = self.params["target"]
        condition = self.params["condition"]
        message = self.params.get("message", "Project must have expense limit or primary project")

        # Parse target as function_name#L<line_number>
        if "#L" not in target:
            raise ValueError(
                f"Invalid target format: {target}. Expected: function_name#L<line_number>"
            )

        function_name, line_part = target.split("#L", 1)
        try:
            target_line = int(line_part)
        except ValueError:
            raise ValueError(
                f"Invalid line number in target: {target}. Expected: function_name#L<line_number>"
            )

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        wrapper = metadata.MetadataWrapper(module)
        transformer = IntroduceAssertionTransformer(function_name, target_line, condition, message)
        modified_tree = wrapper.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class IntroduceAssertionTransformer(cst.CSTTransformer):
    """Transforms a function by introducing an assertion."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, function_name: str, target_line: int, condition: str, message: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to transform
            target_line: Line number where assertion should be inserted
            condition: The assertion condition as a string
            message: The assertion error message
        """
        self.function_name = function_name
        self.target_line = target_line
        self.condition = condition
        self.message = message
        self.current_function: str | None = None
        self.target_index: int | None = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track which function we're currently in and find target statement index."""
        if node.name.value == self.function_name:
            self.current_function = node.name.value

            # Find the index of the statement at or after target_line
            if isinstance(node.body, cst.IndentedBlock):
                for idx, stmt in enumerate(node.body.body):
                    if isinstance(stmt, cst.SimpleStatementLine):
                        for child in stmt.body:
                            try:
                                position = self.get_metadata(metadata.PositionProvider, child)
                                if position.start.line >= self.target_line:
                                    self.target_index = idx
                                    return
                            except KeyError:
                                pass

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and insert assertion if this is the target function."""
        if original_node.name.value == self.function_name and self.target_index is not None:
            condition_expr = cst.parse_expression(self.condition)
            assertion = cst.SimpleStatementLine(
                body=[
                    cst.Assert(
                        test=condition_expr,
                        msg=cst.SimpleString(f'"{self.message}"'),
                    )
                ]
            )

            body = updated_node.body
            if isinstance(body, cst.IndentedBlock):
                new_statements: list[cst.BaseStatement] = list(body.body)
                new_statements.insert(self.target_index, assertion)
                updated_node = updated_node.with_changes(
                    body=cst.IndentedBlock(body=new_statements)
                )

        self.current_function = None
        self.target_index = None
        return updated_node


# Register the command
register_command(IntroduceAssertionCommand)
