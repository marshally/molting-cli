"""Introduce Assertion refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceAssertionCommand(BaseCommand):
    """Make assumptions explicit with an assertion statement.

    The Introduce Assertion refactoring is used to make an assumption that a section
    of code makes about the program state explicit by adding an assertion statement.
    An assertion is a conditional statement that is assumed to be true. If an
    assertion fails at runtime, it indicates a bug in the code.

    **Why use this refactoring:**
    - Clarifies assumptions made by the code, making them visible to future readers
    - Helps catch bugs early by explicitly checking expected conditions
    - Improves code maintainability by documenting implicit assumptions
    - Serves as executable documentation of program state expectations

    **When to use:**
    - You have code that relies on a condition being true but doesn't check it
    - You want to make implicit assumptions explicit and verifiable
    - You're documenting preconditions or invariants that should hold at a point in code
    - You need to catch bugs when assumptions about program state are violated

    **Example:**
    Before:
        def calculate_discount(customer):
            if customer.membership_years > 0:
                discount = customer.base_rate * customer.membership_years
                return discount
            return customer.base_rate

    After:
        def calculate_discount(customer):
            assert customer.base_rate is not None, "Customer must have a base rate set"
            if customer.membership_years > 0:
                discount = customer.base_rate * customer.membership_years
                return discount
            return customer.base_rate
    """

    name = "introduce-assertion"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "condition")

    def _parse_target(self, target: str) -> tuple[str, int]:
        """Parse target parameter into function name and line number.

        Args:
            target: Target string in format function_name#L<line_number>

        Returns:
            Tuple of (function_name, target_line)

        Raises:
            ValueError: If target format is invalid
        """
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

        return function_name, target_line

    def execute(self) -> None:
        """Apply introduce-assertion refactoring using libCST.

        Raises:
            ValueError: If target format is invalid
        """
        target = self.params["target"]
        condition = self.params["condition"]
        message = self.params.get("message", "Project must have expense limit or primary project")

        function_name, target_line = self._parse_target(target)

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
        self.target_index: int | None = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Find target statement index in the target function."""
        if node.name.value == self.function_name:
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

        self.target_index = None
        return updated_node


# Register the command
register_command(IntroduceAssertionCommand)
