"""Inline Temp refactoring - inline temporary variables into their usage."""

import ast
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
            target: Target variable name to inline (e.g., "temp_value" or "ClassName::method_name::temp_value")
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

        Handles both simple names (e.g., "temp_value") and qualified names
        (e.g., "ClassName::method_name").

        Returns:
            Byte offset of the variable identifier in the source code
        """
        # Check if it's a qualified target (e.g., "ClassName::method_name")
        if "::" in self.target:
            return self._get_qualified_offset()
        else:
            # Simple target - just find it in source
            offset = self.source.find(self.target)
            if offset == -1:
                raise ValueError(f"Variable '{self.target}' not found in {self.file_path}")
            return offset

    def _get_qualified_offset(self) -> int:
        """Get the offset of a qualified variable (e.g., ClassName::variable_name).

        Returns:
            Byte offset of the variable definition in the source code
        """
        parts = self.target.split("::")
        if len(parts) == 2:
            class_name, var_name = parts
            method_name = None
        elif len(parts) == 3:
            class_name, method_name, var_name = parts
        else:
            raise ValueError(f"Invalid target format: {self.target}")

        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class definition
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # If method_name is specified, look inside the method
                if method_name:
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == method_name:
                            return self._find_variable_in_scope(var_name, item.lineno)
                    raise ValueError(f"Method '{method_name}' not found in class '{class_name}'")
                else:
                    # Look in all methods of the class for the variable
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            try:
                                return self._find_variable_in_scope(var_name, item.lineno)
                            except ValueError:
                                continue
                    raise ValueError(f"Variable '{var_name}' not found in class '{class_name}'")

        raise ValueError(f"Class '{class_name}' not found in {self.file_path}")

    def _find_variable_in_scope(self, var_name: str, start_line: int) -> int:
        """Find a variable assignment starting from a given line.

        Args:
            var_name: Name of the variable to find
            start_line: Line number to start searching from

        Returns:
            Byte offset of the variable in the source code
        """
        lines = self.source.split('\n')
        offset = 0

        for i, line in enumerate(lines):
            if i < start_line - 1:
                offset += len(line) + 1  # +1 for newline
            else:
                # Search in this and subsequent lines
                remaining_source = '\n'.join(lines[i:])
                var_offset = remaining_source.find(var_name)
                if var_offset != -1:
                    return offset + var_offset

        raise ValueError(f"Variable '{var_name}' not found starting from line {start_line}")
