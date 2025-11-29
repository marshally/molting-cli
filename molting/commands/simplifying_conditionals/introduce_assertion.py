"""Introduce Assertion refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_number, parse_target


class IntroduceAssertionCommand(BaseCommand):
    """Command to make assumptions explicit with an assertion."""

    name = "introduce-assertion"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "condition")

    def _parse_target_and_line(self, target: str) -> tuple[str | None, str, int]:
        """Parse target parameter into class name, function name, and line number.

        Args:
            target: Target string in format:
                - function_name#L<line_number>
                - ClassName::function_name#L<line_number>

        Returns:
            Tuple of (class_name or None, function_name, target_line)

        Raises:
            ValueError: If target format is invalid
        """
        if "#L" not in target:
            raise ValueError(
                f"Invalid target format: {target}. "
                "Expected: function_name#L<line_number> or ClassName::function_name#L<line_number>"
            )

        path_part, line_part = target.split("#", 1)
        target_line = parse_line_number(line_part)

        # Parse the path part (class_name::function_name or just function_name)
        if "::" in path_part:
            class_name, function_name = parse_target(path_part, expected_parts=2)
            return class_name, function_name, target_line
        else:
            return None, path_part, target_line

    def execute(self) -> None:
        """Apply introduce-assertion refactoring using libCST.

        Raises:
            ValueError: If target format is invalid
        """
        target = self.params["target"]
        condition = self.params["condition"]
        message = self.params.get("message", "Project must have expense limit or primary project")

        class_name, function_name, target_line = self._parse_target_and_line(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        wrapper = metadata.MetadataWrapper(module)
        transformer = IntroduceAssertionTransformer(
            class_name, function_name, target_line, condition, message
        )
        modified_tree = wrapper.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class IntroduceAssertionTransformer(cst.CSTTransformer):
    """Transforms a function by introducing an assertion."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        class_name: str | None,
        function_name: str,
        target_line: int,
        condition: str,
        message: str,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the function (or None if top-level)
            function_name: Name of the function to transform
            target_line: Line number where assertion should be inserted
            condition: The assertion condition as a string
            message: The assertion error message
        """
        self.class_name = class_name
        self.function_name = function_name
        self.target_line = target_line
        self.condition = condition
        self.message = message
        self.target_index: int | None = None
        self.current_class: str | None = None
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
        """Find target statement index in the target function."""
        # Check if this is the target function
        if node.name.value == self.function_name:
            # If we're looking for a class-qualified function, check the class
            if self.class_name is not None:
                if self.current_class == self.class_name:
                    self.is_target_matched = True
            else:
                # If no class specified, match any function with this name
                self.is_target_matched = True

            if self.is_target_matched and isinstance(node.body, cst.IndentedBlock):
                # Find the index where the assertion should be inserted
                # We want to insert it at or before the target_line
                for idx, stmt in enumerate(node.body.body):
                    try:
                        position = self.get_metadata(metadata.PositionProvider, stmt)
                        # Insert before the first statement at or after target_line
                        if position.start.line >= self.target_line:
                            self.target_index = idx
                            return
                    except KeyError:
                        pass

                # If no statement found at or after target_line, insert at the end
                if node.body.body:
                    self.target_index = len(node.body.body)
                else:
                    self.target_index = 0

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and insert assertion if this is the target function."""
        if self.is_target_matched and original_node.name.value == self.function_name:
            if self.target_index is not None:
                # Parse the condition and wrap it in parentheses for multi-line formatting
                wrapped_expr = cst.parse_expression(f"({self.condition})")

                assertion = cst.SimpleStatementLine(
                    body=[
                        cst.Assert(
                            test=wrapped_expr,
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

            self.target_index = None
            self.is_target_matched = False

        return updated_node


# Register the command
register_command(IntroduceAssertionCommand)
