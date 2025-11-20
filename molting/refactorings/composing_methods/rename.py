"""Rename refactoring - rename variables, methods, classes, or modules."""

from pathlib import Path
from rope.base.project import Project
from rope.refactor.rename import Rename as RopeRename

from molting.core.refactoring_base import RefactoringBase


class Rename(RefactoringBase):
    """Rename a variable, method, class, or module using rope's rename refactoring."""

    def __init__(self, file_path: str, target: str, new_name: str):
        """Initialize the Rename refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target identifier to rename (e.g., "function_name" or "ClassName::method_name")
            new_name: New name for the target
        """
        self.file_path = Path(file_path)
        self.target = target
        self.new_name = new_name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the rename refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with renamed identifier
        """
        # Use the provided source code
        self.source = source

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Create rename refactoring
            rename_refactor = RopeRename(project, resource, self._get_offset())

            # Apply the rename
            changes = rename_refactor.get_changes(self.new_name)
            project.do(changes)

            # Read the refactored content
            refactored = resource.read()

        finally:
            project.close()

        return refactored

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        # For now, just check that the target exists in the source
        return self.target in source

    def _get_offset(self) -> int:
        """Get the offset of the target in the source code.

        Handles both simple names (e.g., "function_name") and qualified names
        (e.g., "ClassName::method_name").

        Returns:
            Byte offset of the target identifier in the source code
        """
        import ast
        import re

        # Check if it's a qualified target (e.g., "ClassName::method_name")
        if "::" in self.target:
            class_name, member_name = self.target.split("::", 1)
            return self._get_qualified_offset(class_name, member_name)
        else:
            # Simple target - just find it in source
            offset = self.source.find(self.target)
            if offset == -1:
                raise ValueError(f"Target '{self.target}' not found in {self.file_path}")
            return offset

    def _get_qualified_offset(self, class_name: str, member_name: str) -> int:
        """Get the offset of a qualified member (e.g., ClassName::method_name).

        Args:
            class_name: Name of the class
            member_name: Name of the member (method, attribute, etc.)

        Returns:
            Byte offset of the member definition in the source code
        """
        import ast

        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class definition - only look at top-level classes
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Find the member in the class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == member_name:
                        # Get the offset using the line and column
                        # We need to find "def member_name" in the source
                        lines = self.source.split('\n')
                        offset = 0
                        for i, line in enumerate(lines):
                            if i < item.lineno - 1:
                                offset += len(line) + 1  # +1 for newline
                            else:
                                # Found the line, now find the member_name in it
                                col_offset = line.find(member_name)
                                if col_offset != -1:
                                    return offset + col_offset
                                break
                        raise ValueError(f"Could not find offset for {member_name}")
                raise ValueError(f"Member '{member_name}' not found in class '{class_name}'")
        raise ValueError(f"Class '{class_name}' not found in {self.file_path}")
