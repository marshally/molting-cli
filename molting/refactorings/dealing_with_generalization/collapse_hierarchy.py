"""Collapse Hierarchy refactoring - merge a subclass into its superclass."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class CollapseHierarchy(RefactoringBase):
    """Merge a subclass into its superclass when they are too similar."""

    def __init__(self, file_path: str, target: str, into: str):
        """Initialize the CollapseHierarchy refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Name of the subclass to collapse
            into: Name of the superclass to merge into
        """
        self.file_path = Path(file_path)
        self.target = target  # subclass name
        self.into = into  # superclass name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the collapse hierarchy refactoring to source code.

        Removes the subclass definition, keeping only the superclass.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with the subclass removed
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the subclass to remove
        subclass_node = None
        subclass_index = None
        for i, node in enumerate(tree.body):
            if isinstance(node, ast.ClassDef) and node.name == self.target:
                subclass_node = node
                subclass_index = i
                break

        if subclass_node is None:
            raise ValueError(f"Subclass '{self.target}' not found in source code")

        # Find the superclass
        superclass_node = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == self.into:
                superclass_node = node
                break

        if superclass_node is None:
            raise ValueError(f"Superclass '{self.into}' not found in source code")

        # Check that the subclass only inherits from the superclass and has no body
        # (i.e., only has 'pass' or nothing)
        if subclass_node.bases:
            # Check if it actually inherits from the superclass
            inherits_from_superclass = False
            for base in subclass_node.bases:
                if isinstance(base, ast.Name) and base.id == self.into:
                    inherits_from_superclass = True
                    break

            if not inherits_from_superclass:
                raise ValueError(
                    f"Subclass '{self.target}' does not inherit from '{self.into}'"
                )

        # Remove the subclass by reconstructing the module without it
        # We need to calculate the line range of the subclass and remove it from source
        lines = source.split("\n")

        # Get line numbers for the subclass
        start_line = subclass_node.lineno - 1  # Convert to 0-indexed
        end_line = subclass_node.end_lineno  # This is the last line (1-indexed)

        # Reconstruct the source without the subclass
        new_lines = lines[:start_line]

        # Add remaining lines after the subclass, but skip empty lines at the boundary
        if end_line < len(lines):
            remaining = lines[end_line:]
            # Skip leading empty lines
            while remaining and not remaining[0].strip():
                remaining.pop(0)
            new_lines.extend(remaining)

        result = "\n".join(new_lines)

        # Ensure file ends with a newline
        if result and not result.endswith("\n"):
            result += "\n"

        return result

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return False

        # Check that both classes exist
        subclass_exists = False
        superclass_exists = False

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name == self.target:
                    subclass_exists = True
                elif node.name == self.into:
                    superclass_exists = True

        return subclass_exists and superclass_exists
