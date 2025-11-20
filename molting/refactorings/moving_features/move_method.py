"""Move Method refactoring - move a method from one class to another."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class MoveMethod(RefactoringBase):
    """Move a method from one class to another."""

    def __init__(self, file_path: str, source: str, to: str):
        """Initialize the MoveMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            source: Source location in format "ClassName::method_name"
            to: Destination class name
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.source_location = source
        self.destination_class = to

    def apply(self, source: str) -> str:
        """Apply the move method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with method moved
        """
        # Use the provided source code
        self.source = source

        # Parse the source location
        source_class_name, method_name = self._parse_source_location()

        # Parse the AST
        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the source class and method
        source_class = self._find_class(tree, source_class_name)
        if source_class is None:
            raise ValueError(f"Class '{source_class_name}' not found")

        # Find the method in the source class
        method_node = self._find_method_in_class(source_class, method_name)
        if method_node is None:
            raise ValueError(
                f"Method '{method_name}' not found in class '{source_class_name}'"
            )

        # Find the destination class
        dest_class = self._find_class(tree, self.destination_class)
        if dest_class is None:
            raise ValueError(f"Class '{self.destination_class}' not found")

        # Extract the method and move it
        refactored = self._move_method_in_ast(
            tree, source_class_name, method_name, self.destination_class, method_node
        )

        return refactored

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            class_name, method_name = self._parse_source_location()
            tree = ast.parse(source)
            source_class = self._find_class(tree, class_name)
            if source_class is None:
                return False
            method = self._find_method_in_class(source_class, method_name)
            if method is None:
                return False
            dest_class = self._find_class(tree, self.destination_class)
            return dest_class is not None
        except Exception:
            return False

    def _find_class(self, tree: ast.Module, class_name: str) -> ast.ClassDef:
        """Find a class definition in the AST.

        Args:
            tree: The AST module
            class_name: Name of the class to find

        Returns:
            The ClassDef node or None if not found
        """
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
        return None

    def _find_method_in_class(self, class_node: ast.ClassDef, method_name: str) -> ast.FunctionDef:
        """Find a method in a class.

        Args:
            class_node: The ClassDef node
            method_name: Name of the method to find

        Returns:
            The FunctionDef node or None if not found
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == method_name:
                return item
        return None

    def _move_method_in_ast(
        self,
        tree: ast.Module,
        source_class_name: str,
        method_name: str,
        dest_class_name: str,
        method_node: ast.FunctionDef,
    ) -> str:
        """Move a method from one class to another and return the refactored code.

        Args:
            tree: The AST module
            source_class_name: Name of the source class
            method_name: Name of the method to move
            dest_class_name: Name of the destination class
            method_node: The method AST node to move

        Returns:
            The refactored source code as a string
        """
        # For simplicity in green phase, we'll unparse the AST and do text manipulation
        # This is a simplified approach that handles the specific test case
        lines = self.source.split('\n')

        # Find and remove the method from the source class
        removed_method_lines = []
        method_start = None
        method_end = None

        # Find the method's line range in the source
        for i, class_node in enumerate(tree.body):
            if isinstance(class_node, ast.ClassDef) and class_node.name == source_class_name:
                for method_node_in_class in class_node.body:
                    if isinstance(method_node_in_class, ast.FunctionDef) and method_node_in_class.name == method_name:
                        method_start = method_node_in_class.lineno - 1
                        method_end = method_node_in_class.end_lineno

                        # Extract method lines
                        removed_method_lines = lines[method_start:method_end]

                        # Remove from source class
                        del lines[method_start:method_end]
                        break

        if method_start is None:
            raise ValueError(f"Could not find method {method_name}")

        # Now replace the method's calls in source class with delegation
        delegation_code = self._create_delegation_method(method_node, source_class_name)

        # Insert delegation method at original location
        lines.insert(method_start, delegation_code)

        # Now find destination class and add the method there
        refactored_text = '\n'.join(lines)
        lines = refactored_text.split('\n')

        # Find destination class position
        dest_class_start = None
        dest_class_end = None

        for i, class_node in enumerate(tree.body):
            if isinstance(class_node, ast.ClassDef) and class_node.name == dest_class_name:
                dest_class_start = class_node.lineno - 1
                dest_class_end = class_node.end_lineno
                break

        if dest_class_start is None:
            raise ValueError(f"Could not find destination class {dest_class_name}")

        # Insert the moved method into destination class
        # Find the last method in destination class and insert after it
        insert_point = dest_class_end - 1

        # Convert method_node to source code
        moved_method_code = self._indent_code(removed_method_lines, 4)
        lines.insert(insert_point, moved_method_code)

        return '\n'.join(lines)

    def _create_delegation_method(self, method_node: ast.FunctionDef, source_class_name: str) -> str:
        """Create a delegation method in the source class.

        Args:
            method_node: The original method node
            source_class_name: Name of the source class

        Returns:
            The delegation method code
        """
        # Extract the attribute name that holds the destination instance
        # For simplicity, use snake_case of destination class name
        dest_attr = self._to_snake_case(self.destination_class)

        # Get method parameters (excluding self)
        method_args = self._get_method_args_str(method_node)
        call_args = self._get_method_call_args_str(method_node)

        delegation = (
            f"    def {method_node.name}(self{method_args}):\n"
            f"        return self.{dest_attr}.{method_node.name}({call_args})"
        )
        return delegation

    def _get_method_args_str(self, method_node: ast.FunctionDef) -> str:
        """Get method arguments as a string (excluding self).

        Args:
            method_node: The FunctionDef node

        Returns:
            Arguments string like ", arg1, arg2"
        """
        args = []
        for arg in method_node.args.args[1:]:  # Skip self
            args.append(arg.arg)
        if args:
            return ", " + ", ".join(args)
        return ""

    def _get_method_call_args_str(self, method_node: ast.FunctionDef) -> str:
        """Get method call arguments as a string.

        Args:
            method_node: The FunctionDef node

        Returns:
            Arguments string for a method call
        """
        args = []
        for arg in method_node.args.args[1:]:  # Skip self
            args.append(arg.arg)
        return ", ".join(args)

    def _indent_code(self, lines: list, spaces: int) -> str:
        """Indent code lines.

        Args:
            lines: List of code lines
            spaces: Number of spaces to indent

        Returns:
            Indented code as a single string
        """
        indent = " " * spaces
        indented_lines = [indent + line if line.strip() else line for line in lines]
        return '\n'.join(indented_lines)

    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

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
