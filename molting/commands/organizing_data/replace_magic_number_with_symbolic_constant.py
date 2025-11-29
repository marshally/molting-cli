"""Replace Magic Number with Symbolic Constant refactoring command."""

from typing import Optional, Union

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_number, parse_target_with_line
from molting.core.name_conflict_validator import NameConflictValidator


class ReplaceMagicNumberWithSymbolicConstantCommand(BaseCommand):
    """Replace Magic Number with Symbolic Constant refactoring.

    This refactoring transforms magic numbers (unexplained numeric literals) into
    named symbolic constants, improving code readability and maintainability.
    The refactoring extracts a magic number, creates a named constant that
    expresses its meaning, and replaces all occurrences of that number with
    references to the constant.

    **When to use:**
    - A numeric literal has a special meaning that isn't immediately obvious
    - The same magic number appears in multiple places in the codebase
    - You want to make the intent and meaning of numeric values explicit
    - A magic number represents a business rule or domain concept
    - You need to update the value in a single location rather than searching
      for multiple hardcoded occurrences

    **Example:**

    Before:
        def calculate_discount(subtotal: float) -> float:
            if subtotal > 100:
                return subtotal * 0.9  # 10% discount
            return subtotal

    After:
        DISCOUNT_RATE = 0.9
        DISCOUNT_THRESHOLD = 100

        def calculate_discount(subtotal: float) -> float:
            if subtotal > DISCOUNT_THRESHOLD:
                return subtotal * DISCOUNT_RATE
            return subtotal
    """

    name = "replace-magic-number-with-symbolic-constant"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.validate_required_params("target", "name")

        constant_name = self.params["name"]
        if not constant_name.isupper() or not constant_name.replace("_", "").isalnum():
            raise ValueError(f"Constant name '{constant_name}' must be uppercase with underscores")

    def execute(self) -> None:
        """Apply replace-magic-number-with-symbolic-constant refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        constant_name = self.params["name"]

        # Parse target to get function/class name and line number
        class_or_function_name, method_name, line_spec = parse_target_with_line(target)
        target_line = parse_line_number(line_spec)

        source_code = self.file_path.read_text()

        # Check for name conflicts before applying transformation
        validator = NameConflictValidator(source_code)
        validator.validate_constant_name(constant_name)

        # First pass: extract the magic number from the target line
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        extractor = MagicNumberExtractor(class_or_function_name, method_name, target_line)
        wrapper.visit(extractor)

        if extractor.magic_number is None:
            raise ValueError(
                f"Could not find a magic number on line {target_line} in {class_or_function_name}"
            )

        # Second pass: replace magic number and add constant
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ReplaceMagicNumberTransformer(
            class_or_function_name,
            method_name,
            target_line,
            constant_name,
            extractor.magic_number,
        )
        modified_tree = wrapper.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class MagicNumberExtractor(cst.CSTVisitor):
    """Extracts the magic number from the specified line."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_or_function_name: str, method_name: str, target_line: int) -> None:
        """Initialize the extractor.

        Args:
            class_or_function_name: Name of the class or function
            method_name: Name of the method (empty string for function-level)
            target_line: Line number where the magic number is located
        """
        self.class_or_function_name = class_or_function_name
        self.method_name = method_name
        self.target_line = target_line
        self.magic_number: Optional[Union[int, float]] = None
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track when we enter the target function."""
        if self.method_name:
            # Skip function-level tracking if we're looking for a method
            return

        if node.name.value == self.class_or_function_name:
            self.in_target_function = True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track when we leave the target function."""
        if node.name.value == self.class_or_function_name:
            self.in_target_function = False

    def visit_Integer(self, node: cst.Integer) -> None:  # noqa: N802
        """Extract integer literals."""
        if self.in_target_function and self._is_on_target_line(node):
            self.magic_number = int(node.value)

    def visit_Float(self, node: cst.Float) -> None:  # noqa: N802
        """Extract float literals."""
        if self.in_target_function and self._is_on_target_line(node):
            self.magic_number = float(node.value)

    def _is_on_target_line(self, node: cst.CSTNode) -> bool:
        """Check if a node is on the target line."""
        pos = self.get_metadata(metadata.PositionProvider, node)
        return pos.start.line == self.target_line


class ReplaceMagicNumberTransformer(cst.CSTTransformer):
    """Replaces a magic number with a symbolic constant."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        class_or_function_name: str,
        method_name: str,
        target_line: int,
        constant_name: str,
        magic_number: Union[int, float],
    ) -> None:
        """Initialize the transformer.

        Args:
            class_or_function_name: Name of the class or function
            method_name: Name of the method (empty string for function-level)
            target_line: Line number where the magic number is located
            constant_name: Name for the symbolic constant
            magic_number: The magic number value to replace
        """
        self.class_or_function_name = class_or_function_name
        self.method_name = method_name
        self.target_line = target_line
        self.constant_name = constant_name
        self.magic_number = magic_number
        self.in_target_function = False
        self.constant_added = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track when we enter the target function."""
        if self.method_name:
            # Skip function-level tracking if we're looking for a method
            return

        if node.name.value == self.class_or_function_name:
            self.in_target_function = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Track when we leave the target function."""
        if original_node.name.value == self.class_or_function_name:
            self.in_target_function = False
        return updated_node

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the constant at module level."""
        if self.constant_added:
            return updated_node

        # Create the constant assignment
        constant_value = (
            cst.Float(str(self.magic_number))
            if isinstance(self.magic_number, float)
            else cst.Integer(str(self.magic_number))
        )

        constant_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.constant_name))],
                    value=constant_value,
                )
            ]
        )

        # Add constant at the beginning of the module with blank lines after
        new_body = [
            constant_assignment,
            cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            *updated_node.body,
        ]

        self.constant_added = True
        return updated_node.with_changes(body=new_body)

    def _should_replace_number(self, node: Union[cst.Integer, cst.Float]) -> bool:
        """Check if a number node should be replaced with the constant.

        Args:
            node: The number node to check

        Returns:
            True if the node should be replaced
        """
        if not self.in_target_function:
            return False

        if not self._is_on_target_line(node):
            return False

        node_value = int(node.value) if isinstance(node, cst.Integer) else float(node.value)
        return node_value == self.magic_number

    def leave_Integer(  # noqa: N802
        self, original_node: cst.Integer, updated_node: cst.Integer
    ) -> Union[cst.Integer, cst.Name]:
        """Replace integer literals with the constant name."""
        if self._should_replace_number(original_node):
            return cst.Name(self.constant_name)
        return updated_node

    def leave_Float(  # noqa: N802
        self, original_node: cst.Float, updated_node: cst.Float
    ) -> Union[cst.Float, cst.Name]:
        """Replace float literals with the constant name."""
        if self._should_replace_number(original_node):
            return cst.Name(self.constant_name)
        return updated_node

    def _is_on_target_line(self, node: cst.CSTNode) -> bool:
        """Check if a node is on the target line."""
        pos = self.get_metadata(metadata.PositionProvider, node)
        return pos.start.line == self.target_line


# Register the command
register_command(ReplaceMagicNumberWithSymbolicConstantCommand)
