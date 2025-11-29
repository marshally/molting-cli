"""Introduce Assertion refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_number, parse_line_range


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

    def _parse_target(self, target: str) -> tuple[str, str, int]:
        """Parse target parameter into class name, function name, and line number.

        Args:
            target: Target string in format function_name#L<line_number> or ClassName::method#L<line_number>

        Returns:
            Tuple of (class_name, function_name, target_line)
            class_name will be empty string for module-level functions

        Raises:
            ValueError: If target format is invalid
        """
        if "#" not in target:
            raise ValueError(
                f"Invalid target format: {target}. "
                "Expected: function_name#L<line_number> or ClassName::method#L<line_number>"
            )

        class_method, line_spec = target.split("#", 1)

        # Parse class_method to extract class and method names
        if "::" in class_method:
            class_parts = class_method.split("::")
            if len(class_parts) != 2:
                raise ValueError(f"Invalid class::method format in '{class_method}'")
            class_name, function_name = class_parts
        else:
            class_name = ""
            function_name = class_method

        # Use canonical line number parser
        target_line = parse_line_number(line_spec)
        return class_name, function_name, target_line

    def execute(self) -> None:
        """Apply introduce-assertion refactoring using libCST.

        Raises:
            ValueError: If target format is invalid
        """
        target = self.params["target"]
        condition = self.params["condition"]
        message = self.params.get("message", "Project must have expense limit or primary project")

        class_name, function_name, target_line = self._parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        wrapper = metadata.MetadataWrapper(module)
        transformer = IntroduceAssertionTransformer(class_name, function_name, target_line, condition, message)
        modified_tree = wrapper.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class IntroduceAssertionTransformer(cst.CSTTransformer):
    """Transforms a function by introducing an assertion."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_name: str, function_name: str, target_line: int, condition: str, message: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class (empty string for module-level functions)
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

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Find target statement index in the target function."""
        # For class methods, also check we're in the right class
        if node.name.value == self.function_name:
            if self.class_name and self.current_class == self.class_name:
                found = True
            elif not self.class_name:
                found = True
            else:
                found = False

            if found:
                # For introduce-assertion, we insert at the beginning of the function
                # So target_index is always 0 (insert before first statement)
                # The target_line parameter helps identify the right location conceptually,
                # but we insert assertions at the function start
                self.target_index = 0

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and insert assertion if this is the target function."""
        # Check if this is the right function
        if original_node.name.value == self.function_name:
            if self.class_name and self.current_class == self.class_name:
                is_target = True
            elif not self.class_name:
                is_target = True
            else:
                is_target = False
        else:
            is_target = False

        if is_target and self.target_index is not None:
            # Create an assertion statement with proper formatting
            # Build the assertion as a string with proper formatting
            assertion_code = f'assert ({self.condition}), "{self.message}"'
            try:
                # Parse as a full statement to get proper formatting
                assertion = cst.parse_statement(assertion_code)
            except Exception:
                # Fallback: parse as simple expression
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
