"""Move Method refactoring - move a method from one class to another."""

from pathlib import Path
from rope.base.project import Project
from rope.refactor.move import create_move

from molting.core.refactoring_base import RefactoringBase


class MoveMethod(RefactoringBase):
    """Move a method from one class to another using rope's move refactoring."""

    def __init__(self, file_path: str, source: str, to: str):
        """Initialize the MoveMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            source: Source location in format "ClassName::method_name"
            to: Destination attribute name in the source class (e.g., "account_type")
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.source_location = source
        self.destination_attr = to

    def apply(self, source: str) -> str:
        """Apply the move method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with method moved
        """
        # Use the provided source code
        self.source = source

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Parse the source location
            class_name, method_name = self._parse_source_location()

            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Get the offset of the method
            offset = self._get_method_offset(class_name, method_name)

            # Find the attribute that refers to the destination class
            dest_attr = self._find_destination_attr(class_name)

            # Create move refactoring
            mover = create_move(project, resource, offset)

            # Get changes for moving to destination
            changes = mover.get_changes(dest_attr)
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
        class_name, method_name = self._parse_source_location()
        return f"{class_name}" in source and f"{method_name}" in source

    def _parse_source_location(self) -> tuple:
        """Parse the source location string.

        Format: "ClassName::method_name"

        Returns:
            Tuple of (class_name, method_name)

        Raises:
            ValueError: If source location format is invalid
        """
        if "::" not in self.source_location:
            raise ValueError(
                f"Invalid source location format: {self.source_location}. "
                "Expected 'ClassName::method_name'"
            )

        class_name, method_name = self.source_location.split("::", 1)
        return class_name, method_name

    def _find_destination_attr(self, class_name: str) -> str:
        """Find the attribute in the source class that references the destination class.

        Args:
            class_name: Name of the source class

        Returns:
            Name of the attribute that holds the destination class instance
        """
        import ast

        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class definition
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Look for attributes in the class that reference the destination
                # We'll check __init__ for assignments like self.account_type = account_type
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        # Check assignments in __init__
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Assign):
                                # Look for self.attr_name assignments
                                for target in stmt.targets:
                                    if isinstance(target, ast.Attribute):
                                        if (isinstance(target.value, ast.Name) and
                                            target.value.id == "self"):
                                            attr_name = target.attr
                                            # Check if this might be the destination
                                            # For now, try to match with destination_attr hint
                                            if attr_name in self.source:
                                                return attr_name

                # If no attribute found, just return the snake_case version of destination
                # e.g., AccountType -> account_type
                snake_case = self._to_snake_case(self.destination_attr)
                if snake_case in self.source:
                    return snake_case

        raise ValueError(
            f"Could not find destination attribute for {self.destination_attr} "
            f"in class {class_name}"
        )

    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _get_method_offset(self, class_name: str, method_name: str) -> int:
        """Get the offset of a method in the source code.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method

        Returns:
            Byte offset of the method definition in the source code
        """
        import ast

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
                                # Found the line, now find the method name in it
                                col_offset = line.find(method_name)
                                if col_offset != -1:
                                    return offset + col_offset
                                break
                        raise ValueError(f"Could not find offset for {method_name}")
                raise ValueError(f"Method '{method_name}' not found in class '{class_name}'")
        raise ValueError(f"Class '{class_name}' not found in {self.file_path}")
