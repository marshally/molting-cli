"""Introduce Parameter refactoring - add a parameter to a method."""

from pathlib import Path
from rope.base.project import Project
from rope.refactor.introduce_parameter import IntroduceParameter as RopeIntroduceParameter

from molting.core.refactoring_base import RefactoringBase


class IntroduceParameter(RefactoringBase):
    """Add a new parameter to a method using rope's introduce parameter refactoring."""

    def __init__(self, file_path: str, target: str, name: str, default: str = None):
        """Initialize the IntroduceParameter refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method (e.g., "ClassName::method_name")
            name: Name of the new parameter
            default: Default value for the new parameter (optional)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.name = name
        self.default = default
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the introduce parameter refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new parameter added
        """
        self.source = source

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Get the offset of the method
            offset = self._get_method_offset()

            # Create introduce parameter refactoring
            refactor = RopeIntroduceParameter(
                project, resource, offset, self.name, default_value=self.default
            )

            # Apply the refactoring
            changes = refactor.get_changes()
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
        # Check that the target method exists in the source
        if "::" in self.target:
            class_name, method_name = self.target.split("::", 1)
            return f"def {method_name}" in source and f"class {class_name}" in source
        else:
            return f"def {self.target}" in source

    def _get_method_offset(self) -> int:
        """Get the offset of the target method in the source code.

        Handles qualified targets (e.g., "ClassName::method_name").

        Returns:
            Byte offset of the method definition in the source code
        """
        import ast

        if "::" not in self.target:
            raise ValueError(f"Target '{self.target}' must be in format 'ClassName::method_name'")

        class_name, method_name = self.target.split("::", 1)

        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class definition
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Find the method in the class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        # Get the offset using the line and column
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
