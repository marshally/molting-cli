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

        # Write source to file so rope can read it
        self.file_path.write_text(source)

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
        # Check if it's a qualified target (e.g., "function_name::var_name", "ClassName::method_name", or "ClassName::method_name::var_name")
        if "::" in self.target:
            parts = self.target.split("::")
            if len(parts) == 2:
                container_name, var_name = parts
                # Check if it's a function or class
                try:
                    tree = ast.parse(self.source)
                except SyntaxError as e:
                    raise ValueError(f"Failed to parse source code: {e}")

                # Look for a function with this name first
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == container_name:
                        # It's a function - find the variable in it
                        return self._find_variable_in_scope(var_name, node.lineno)

                # Not a function, try as a class
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.name == container_name:
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                try:
                                    return self._find_variable_in_scope(var_name, item.lineno)
                                except ValueError:
                                    continue
                        raise ValueError(
                            f"Variable '{var_name}' not found in class '{container_name}'"
                        )

                raise ValueError(
                    f"Function or class '{container_name}' not found in {self.file_path}"
                )

            elif len(parts) == 3:
                class_name, method_name, var_name = parts
                # Use the base class method to get the method offset
                method_offset = self.calculate_qualified_offset(
                    self.source, class_name, method_name
                )
                # Now find the variable starting from that method
                return self._find_variable_in_scope_from_offset(var_name, method_offset)
            else:
                raise ValueError(f"Invalid target format: {self.target}")
        else:
            # Simple target - just find it in source
            offset = self.source.find(self.target)
            if offset == -1:
                raise ValueError(f"Variable '{self.target}' not found in {self.file_path}")
            return offset

    def _find_variable_in_scope(self, var_name: str, start_line: int) -> int:
        """Find a variable assignment starting from a given line.

        Args:
            var_name: Name of the variable to find
            start_line: Line number to start searching from

        Returns:
            Byte offset of the variable in the source code
        """
        lines = self.source.split("\n")
        offset = 0

        for i, line in enumerate(lines):
            if i < start_line - 1:
                offset += len(line) + 1  # +1 for newline
            else:
                # Search in this and subsequent lines
                remaining_source = "\n".join(lines[i:])
                var_offset = remaining_source.find(var_name)
                if var_offset != -1:
                    return offset + var_offset

        raise ValueError(f"Variable '{var_name}' not found starting from line {start_line}")

    def _find_variable_in_scope_from_offset(self, var_name: str, start_offset: int) -> int:
        """Find a variable assignment starting from a given byte offset.

        Args:
            var_name: Name of the variable to find
            start_offset: Byte offset to start searching from

        Returns:
            Byte offset of the variable in the source code
        """
        remaining_source = self.source[start_offset:]
        var_offset = remaining_source.find(var_name)
        if var_offset != -1:
            return start_offset + var_offset

        raise ValueError(f"Variable '{var_name}' not found starting from offset {start_offset}")
