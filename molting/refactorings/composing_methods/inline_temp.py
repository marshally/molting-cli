"""Inline Temp refactoring - inline temporary variables into their usage."""

from pathlib import Path
from rope.base.project import Project
from rope.refactor.inline import create_inline

from molting.core.refactoring_base import RefactoringBase


class InlineTemp(RefactoringBase):
    """Inline a temporary variable by replacing all references with its value."""

    def __init__(self, file_path: str, target: str):
        """Initialize the InlineTemp refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target variable name to inline (e.g., "temp_value")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the inline temp refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with variable inlined
        """
        # Use the provided source code
        self.source = source

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Get the offset of the variable
            offset = self._get_variable_offset()

            # Create inline refactoring for the variable
            inline_refactor = create_inline(project, resource, offset)

            # Apply the inline refactoring
            changes = inline_refactor.get_changes()
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
        # Check that the target exists in the source
        return self.target in source

    def _get_variable_offset(self) -> int:
        """Get the offset of the variable in the source code.

        Returns:
            Byte offset of the variable identifier in the source code
        """
        # Find the variable name in the source code
        offset = self.source.find(self.target)
        if offset == -1:
            raise ValueError(f"Variable '{self.target}' not found in {self.file_path}")
        return offset
