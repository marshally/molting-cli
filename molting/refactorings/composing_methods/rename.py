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

        # Write source to file so rope can read it
        self.file_path.write_text(source)

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
        # Check if it's a qualified target (e.g., "ClassName::method_name")
        if "::" in self.target:
            class_name, member_name = self.target.split("::", 1)
            # Use the base class method to get the qualified offset
            return self.calculate_qualified_offset(self.source, class_name, member_name)
        else:
            # Simple target - just find it in source
            offset = self.source.find(self.target)
            if offset == -1:
                raise ValueError(f"Target '{self.target}' not found in {self.file_path}")
            return offset
