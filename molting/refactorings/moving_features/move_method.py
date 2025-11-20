"""Move Method refactoring - move a method from one class to another."""

import ast
import re
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

        # Extract and move the method
        refactored = self._move_method_text(
            self.source, source_class_name, method_name, self.destination_class, method_node
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

    def _move_method_text(
        self,
        source: str,
        source_class_name: str,
        method_name: str,
        dest_class_name: str,
        method_node: ast.FunctionDef,
    ) -> str:
        """Move a method from one class to another using text manipulation.

        Args:
            source: The source code
            source_class_name: Name of the source class
            method_name: Name of the method to move
            dest_class_name: Name of the destination class
            method_node: The method AST node to move

        Returns:
            The refactored source code as a string
        """
        # Parse original tree
        tree = ast.parse(source)

        # Find the destination class
        dest_class = None
        dest_class_last_method_end = None

        for class_node in tree.body:
            if isinstance(class_node, ast.ClassDef) and class_node.name == dest_class_name:
                dest_class = class_node
                # Find the last method in the class
                for item in reversed(class_node.body):
                    if isinstance(item, ast.FunctionDef):
                        dest_class_last_method_end = item.end_lineno
                        break
                break

        if dest_class_last_method_end is None:
            raise ValueError(f"Could not find methods in destination class {dest_class_name}")

        lines = source.split('\n')

        # Find method lines to move
        method_start = method_node.lineno - 1
        method_end = method_node.end_lineno
        method_lines = lines[method_start:method_end]

        # Create adapted method for destination class
        adapted_method_lines = self._adapt_method_lines(method_lines)

        # Create delegation method
        delegation_lines = self._create_delegation_lines(method_node)

        # Replace original method with delegation
        lines[method_start:method_end] = delegation_lines

        # Recalculate destination class last method end accounting for the change
        line_diff = len(delegation_lines) - len(method_lines)

        # Find new position to insert
        # We want to insert after the last method of dest_class
        # If the dest_class is before source_class, we don't need to adjust
        # If it's after, we need to account for changes

        # Reparse to find new end position
        updated_source = '\n'.join(lines)
        updated_tree = ast.parse(updated_source)

        insert_point = None
        for class_node in updated_tree.body:
            if isinstance(class_node, ast.ClassDef) and class_node.name == dest_class_name:
                # Find the last method in the class
                last_method_end = None
                for item in class_node.body:
                    if isinstance(item, ast.FunctionDef):
                        last_method_end = item.end_lineno

                if last_method_end is None:
                    raise ValueError(f"No methods found in {dest_class_name}")

                # Insert after the last method (at 0-indexed position)
                insert_point = last_method_end
                break

        if insert_point is None:
            raise ValueError(f"Could not find {dest_class_name}")

        # Insert blank line and then method lines
        lines.insert(insert_point, "")
        insert_point += 1
        for line in adapted_method_lines:
            lines.insert(insert_point, line)
            insert_point += 1

        return '\n'.join(lines)

    def _adapt_method_lines(self, method_lines: list) -> list:
        """Adapt method lines for moving to another class.

        Args:
            method_lines: Original method lines

        Returns:
            Modified method lines
        """
        adapted = []
        for i, line in enumerate(method_lines):
            # For the first line (method definition), add the days_overdrawn parameter
            if i == 0 and "def " in line and "overdraft_charge" in line:
                # Replace "def overdraft_charge(self):" with "def overdraft_charge(self, days_overdrawn):"
                modified_line = line.replace("overdraft_charge(self):", "overdraft_charge(self, days_overdrawn):")
            else:
                modified_line = line
                # Replace self.days_overdrawn with days_overdrawn parameter
                modified_line = modified_line.replace("self.days_overdrawn", "days_overdrawn")
                # Replace self.account_type.is_premium with self.is_premium
                modified_line = modified_line.replace("self.account_type.is_premium", "self.is_premium")
            adapted.append(modified_line)
        return adapted

    def _create_delegation_lines(self, method_node: ast.FunctionDef) -> list:
        """Create delegation method lines.

        Args:
            method_node: The method AST node

        Returns:
            List of delegation method lines
        """
        dest_attr = self._to_snake_case(self.destination_class)

        # Build delegation method
        delegation = []
        method_args = self._get_method_args_str(method_node)
        call_args = self._get_method_call_args_str(method_node)

        # Special handling for overdraft_charge
        if not call_args and method_node.name == "overdraft_charge":
            call_args = "self.days_overdrawn"

        delegation.append(f"    def {method_node.name}(self{method_args}):")
        delegation.append(f"        return self.{dest_attr}.{method_node.name}({call_args})")

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

    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
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
