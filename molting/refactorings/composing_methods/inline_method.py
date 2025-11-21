"""Inline Method refactoring - replace calls to a method with the method's body."""

from pathlib import Path

from rope.base.project import Project
from rope.refactor.inline import InlineMethod as RopeInlineMethod

from molting.core.refactoring_base import RefactoringBase


class InlineMethod(RefactoringBase):
    """Inline a method by replacing calls with the method's body using rope's inline refactoring."""

    def __init__(self, file_path: str, target: str):
        """Initialize the InlineMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method to inline (e.g., "ClassName::method_name")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the inline method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with method inlined
        """
        # Use the provided source code
        self.source = source

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Create inline refactoring
            inline_refactor = RopeInlineMethod(project, resource, self._get_offset())

            # Apply the inline
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
        # For now, just check that the target exists in the source
        return self.target in source

    def _get_offset(self) -> int:
        """Get the offset of the target method in the source code.

        Handles qualified names (e.g., "ClassName::method_name").

        Returns:
            Byte offset of the method definition in the source code
        """
        # Check if it's a qualified target (e.g., "ClassName::method_name")
        if "::" in self.target:
            class_name, method_name = self.target.split("::", 1)
            # Use the base class method to get the qualified offset
            return self.calculate_qualified_offset(self.source, class_name, method_name)
        else:
            raise ValueError(
                f"Target must be in format 'ClassName::method_name', got '{self.target}'"
            )
