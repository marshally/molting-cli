"""Replace Magic Number with Symbolic Constant refactoring."""

import re
from pathlib import Path

import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class ReplaceMagicNumberWithSymbolicConstant(RefactoringBase):
    """Replace a magic number with a named symbolic constant."""

    def __init__(self, file_path: str, target: str, magic_number: str, constant_name: str):
        """Initialize the refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "method#L10")
            magic_number: The numeric literal to replace (as string)
            constant_name: Name of the constant to create
        """
        self.file_path = Path(file_path)
        self.target = target
        self.magic_number = magic_number
        self.constant_name = constant_name
        self.source = self.file_path.read_text()
        self.line_number = self._parse_line_number()

    def _parse_line_number(self) -> int:
        """Parse line number from target specification.

        Returns:
            Line number as integer
        """
        match = re.search(r'#L(\d+)', self.target)
        if match:
            return int(match.group(1))
        raise ValueError(f"Invalid target format: {self.target}. Expected format: 'method#L10'")

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code
        """
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Create a transformer to replace the magic number with metadata support
        wrapper = cst.metadata.MetadataWrapper(tree)
        transformer = MagicNumberReplacer(
            self.magic_number,
            self.constant_name,
            self.line_number
        )

        # Apply the transformation
        modified_tree = wrapper.visit(transformer)

        # Add constant declaration at module level
        constant_stmt = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.constant_name))],
                    value=cst.Float(self.magic_number) if '.' in self.magic_number else cst.Integer(self.magic_number)
                )
            ]
        )

        # Insert the constant at the beginning of the module
        new_body = [constant_stmt] + list(modified_tree.body)
        modified_tree = modified_tree.with_changes(body=new_body)

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        return True


class MagicNumberReplacer(cst.CSTTransformer):
    """Replaces magic numbers with constant names."""

    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(self, magic_number: str, constant_name: str, line_number: int):
        """Initialize the transformer.

        Args:
            magic_number: The numeric literal to replace (as string)
            constant_name: Name of the constant to replace with
            line_number: Line number where replacement should happen (1-indexed)
        """
        self.magic_number = magic_number
        self.constant_name = constant_name
        self.line_number = line_number

    def leave_Float(self, original_node: cst.Float, updated_node: cst.Float) -> cst.BaseExpression:
        """Replace float literals that match the magic number."""
        if original_node.value == self.magic_number:
            return cst.Name(self.constant_name)
        return updated_node

    def leave_Integer(self, original_node: cst.Integer, updated_node: cst.Integer) -> cst.BaseExpression:
        """Replace integer literals that match the magic number."""
        if original_node.value == self.magic_number:
            return cst.Name(self.constant_name)
        return updated_node
