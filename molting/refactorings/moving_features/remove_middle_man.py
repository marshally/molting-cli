"""Remove Middle Man refactoring - remove delegation methods from a class."""

import ast
from pathlib import Path
from typing import List, Optional, Tuple

from molting.core.refactoring_base import RefactoringBase


class RemoveMiddleMan(RefactoringBase):
    """Remove delegation methods that just delegate to another object's methods."""

    def __init__(self, file_path: str, target: str, methods: Optional[str] = None):
        """Initialize the RemoveMiddleMan refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: The class with delegation methods (e.g., "Person")
            methods: Comma-separated delegation methods to remove (optional)
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.target_class = target
        self.methods_to_remove = [m.strip() for m in (methods or "").split(",")] if methods else []

    def apply(self, source: str) -> str:
        """Apply the remove middle man refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with delegation methods removed
        """
        # Use the provided source code
        self.source = source

        # Parse the AST
        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class
        target_class = self.find_class_def(tree, self.target_class)
        if target_class is None:
            raise ValueError(f"Class '{self.target_class}' not found")

        # Find delegation methods if not specified
        if not self.methods_to_remove:
            self.methods_to_remove = self._find_delegation_methods(tree, target_class)

        # If no delegation methods found, return unchanged
        if not self.methods_to_remove:
            return self.source

        # Remove the delegation methods
        refactored = self._remove_delegation_methods(
            self.source, self.target_class, self.methods_to_remove
        )

        # Also make any private fields public by removing underscore prefix
        refactored = self._make_delegate_fields_public(refactored, self.target_class)

        return refactored

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)
            target_class = self.find_class_def(tree, self.target_class)
            if target_class is None:
                return False

            # Check if delegation methods exist
            if not self.methods_to_remove:
                methods = self._find_delegation_methods(tree, target_class)
                return len(methods) > 0

            # Check if all specified methods exist
            for method_name in self.methods_to_remove:
                method = self.find_method_in_class(target_class, method_name)
                if method is None:
                    return False

            return True
        except Exception:
            return False

    def _find_delegation_methods(self, tree: ast.AST, target_class: ast.ClassDef) -> List[str]:
        """Find all delegation methods in a class.

        A delegation method is one that just delegates to another attribute's method.
        For example: def get_manager(self): return self._department.manager

        Args:
            tree: The AST tree
            target_class: The class to analyze

        Returns:
            List of method names that are simple delegations
        """
        delegation_methods = []

        for node in target_class.body:
            if isinstance(node, ast.FunctionDef) and node.name != "__init__":
                if self._is_delegation_method(node):
                    delegation_methods.append(node.name)

        return delegation_methods

    def _is_delegation_method(self, method: ast.FunctionDef) -> bool:
        """Check if a method is a simple delegation method.

        Args:
            method: The method to check

        Returns:
            True if the method just delegates to another attribute
        """
        # Must have exactly one statement (the return)
        if len(method.body) != 1:
            return False

        stmt = method.body[0]

        # Must be a return statement
        if not isinstance(stmt, ast.Return):
            return False

        # The return value should be an attribute access (e.g., self._department.manager)
        if isinstance(stmt.value, ast.Attribute):
            return True

        return False

    def _remove_delegation_methods(
        self, source: str, class_name: str, method_names: List[str]
    ) -> str:
        """Remove delegation methods from the class.

        Args:
            source: The source code
            class_name: The class name
            method_names: Names of methods to remove

        Returns:
            Source code with methods removed
        """
        lines = source.splitlines(keepends=True)

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        target_class = self.find_class_def(tree, class_name)
        if target_class is None:
            return source

        # Collect line ranges for methods to remove (in reverse order to remove from bottom up)
        ranges_to_remove = []

        for node in target_class.body:
            if isinstance(node, ast.FunctionDef) and node.name in method_names:
                # Get the line numbers (1-indexed in AST)
                start_line = node.lineno - 1  # Convert to 0-indexed
                end_line = node.end_lineno  # This is inclusive, convert to exclusive

                ranges_to_remove.append((start_line, end_line))

        # Sort ranges in reverse order (highest first) to maintain line number accuracy
        ranges_to_remove.sort(reverse=True)

        # Remove the ranges
        for start_line, end_line in ranges_to_remove:
            # Remove lines, handling potential blank lines before
            del lines[start_line:end_line]

        # Join back and clean up excess blank lines
        result = "".join(lines)

        # Clean up multiple consecutive blank lines (more than 2)
        while "\n\n\n" in result:
            result = result.replace("\n\n\n", "\n\n")

        return result

    def _make_delegate_fields_public(self, source: str, class_name: str) -> str:
        """Make delegate fields public by removing underscore prefix.

        Args:
            source: The source code
            class_name: The class name

        Returns:
            Source code with fields made public
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        target_class = self.find_class_def(tree, class_name)
        if target_class is None:
            return source

        # Find delegate field assignments in __init__
        delegate_fields = self._find_delegate_fields(target_class)

        result = source
        for private_name, public_name in delegate_fields:
            # Replace private field assignments with public ones
            result = result.replace(f"self.{private_name} =", f"self.{public_name} =")

        return result

    def _find_delegate_fields(self, class_node: ast.ClassDef) -> List[Tuple[str, str]]:
        """Find delegate fields (private fields that are delegated to).

        Args:
            class_node: The class AST node

        Returns:
            List of (private_name, public_name) tuples
        """
        delegate_fields: List[Tuple[str, str]] = []

        # Look for __init__ method
        init_method = self.find_method_in_class(class_node, "__init__")
        if init_method is None:
            return delegate_fields

        # Look for assignments like self._department = department
        for node in ast.walk(init_method):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        if isinstance(target.value, ast.Name) and target.value.id == "self":
                            field_name = target.attr
                            # If it's a private field, mark it for making public
                            if field_name.startswith("_"):
                                public_name = field_name[1:]  # Remove leading underscore
                                delegate_fields.append((field_name, public_name))

        return delegate_fields
