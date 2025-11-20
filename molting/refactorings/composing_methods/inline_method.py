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
        import ast

        # Check if it's a qualified target (e.g., "ClassName::method_name")
        if "::" in self.target:
            class_name, method_name = self.target.split("::", 1)
            return self._get_qualified_offset(class_name, method_name)
        else:
            raise ValueError(f"Target must be in format 'ClassName::method_name', got '{self.target}'")

    def _get_qualified_offset(self, class_name: str, method_name: str) -> int:
        """Get the offset of a qualified method (e.g., ClassName::method_name).

        Args:
            class_name: Name of the class
            method_name: Name of the method

        Returns:
            Byte offset of the method definition in the source code
        """
        import ast

        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class definition - only look at top-level classes
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Find the method in the class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        # Get the offset using the line and column
                        # We need to find "def method_name" in the source
                        lines = self.source.split('\n')
                        offset = 0
                        for i, line in enumerate(lines):
                            if i < item.lineno - 1:
                                offset += len(line) + 1  # +1 for newline
                            else:
                                # Found the line, now find the method_name in it
                                col_offset = line.find(method_name)
                                if col_offset != -1:
                                    return offset + col_offset
                                break
                        raise ValueError(f"Could not find offset for {method_name}")
                raise ValueError(f"Method '{method_name}' not found in class '{class_name}'")
        raise ValueError(f"Class '{class_name}' not found in {self.file_path}")
