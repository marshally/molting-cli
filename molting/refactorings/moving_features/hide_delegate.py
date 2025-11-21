"""Hide Delegate refactoring - create delegation methods on the server."""

import ast
from pathlib import Path
from typing import Optional

from molting.core.refactoring_base import RefactoringBase


class HideDelegate(RefactoringBase):
    """Create delegation methods on the server object to hide the delegate."""

    def __init__(self, file_path: str, target: str):
        """Initialize the HideDelegate refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field as "ClassName::field_name" (e.g., "Person::department")
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.target = target

    def apply(self, source: str) -> str:
        """Apply the hide delegate refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with delegation methods added
        """
        # Parse the target (ClassName::field_name)
        class_name, field_name = self.parse_qualified_target(self.target)

        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class
        target_class = self.find_class_def(tree, class_name)
        if target_class is None:
            raise ValueError(f"Class '{class_name}' not found")

        # Find the field in the class
        field_assignment = self._find_field_assignment(target_class, field_name)
        if field_assignment is None:
            raise ValueError(f"Field '{field_name}' not found in class '{class_name}'")

        # Get the delegate field value to find what methods are accessed on it
        delegate_methods = self._find_delegate_methods(source, class_name, field_name)

        # Rename the field to be private (add underscore prefix)
        self._rename_field_to_private(target_class, field_name)

        # Add delegation methods for each accessed method on the delegate
        for method_name in delegate_methods:
            self._add_delegation_method(target_class, field_name, method_name)

        # Fix missing locations for all nodes
        ast.fix_missing_locations(tree)

        # Convert back to source code
        return ast.unparse(tree)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            class_name, field_name = self.parse_qualified_target(self.target)
            tree = ast.parse(source)

            target_class = self.find_class_def(tree, class_name)
            if target_class is None:
                return False

            # Check that the field exists
            return self._find_field_assignment(target_class, field_name) is not None
        except Exception:
            return False

    def _find_field_assignment(
        self, class_node: ast.ClassDef, field_name: str
    ) -> Optional[ast.Assign]:
        """Find a field assignment in a class __init__ method.

        Args:
            class_node: The ClassDef AST node
            field_name: The name of the field

        Returns:
            The assignment statement AST node or None if not found
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if (
                                    isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                    and target.attr == field_name
                                ):
                                    return stmt
        return None

    def _find_delegate_methods(self, source: str, class_name: str, field_name: str) -> set[str]:
        """Find what methods/properties the delegate class exposes.

        Args:
            source: Python source code to analyze
            class_name: The class containing the field
            field_name: The field name

        Returns:
            Set of method/property names available on the delegate class
        """
        # First, find the delegate class by looking at the __init__ parameter type
        tree = ast.parse(source)
        delegate_class_name = None

        # Find the parameter for this field in the __init__ method
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        # Look at the parameters
                        for arg in item.args.args:
                            if arg.arg == field_name:
                                # The parameter name matches the field name
                                # The type hint tells us the class (if available)
                                if arg.annotation is not None and isinstance(
                                    arg.annotation, ast.Name
                                ):
                                    delegate_class_name = arg.annotation.id
                                else:
                                    # If no type hint, infer from parameter name
                                    delegate_class_name = field_name.capitalize()
                        break

        if delegate_class_name is None:
            # Try to infer the delegate class name from the parameter
            # For "department" field, try to find "Department" class
            delegate_class_name = field_name.capitalize()

        # Now find all public attributes/methods in the delegate class
        delegate_methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == delegate_class_name:
                # Find all attributes assigned in __init__
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        for stmt in item.body:
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Attribute):
                                        if (
                                            isinstance(target.value, ast.Name)
                                            and target.value.id == "self"
                                        ):
                                            delegate_methods.add(target.attr)

        return delegate_methods

    def _rename_field_to_private(self, class_node: ast.ClassDef, field_name: str) -> None:
        """Rename a field to be private (add underscore prefix).

        Args:
            class_node: The ClassDef AST node
            field_name: The field name to make private
        """
        private_name = f"_{field_name}"

        # Find __init__ and rename the field assignment
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if (
                                    isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                    and target.attr == field_name
                                ):
                                    target.attr = private_name

    def _add_delegation_method(
        self, class_node: ast.ClassDef, field_name: str, method_name: str
    ) -> None:
        """Add a delegation method to the class.

        Args:
            class_node: The ClassDef AST node
            field_name: The field name (will be made private)
            method_name: The method/property name to delegate
        """
        private_field_name = f"_{field_name}"
        getter_method_name = f"get_{method_name}"

        # Create the delegation method:
        # def get_manager(self):
        #     return self._department.manager
        method_def = ast.FunctionDef(
            name=getter_method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self", annotation=None)],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=[
                ast.Return(
                    value=ast.Attribute(
                        value=ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr=private_field_name,
                            ctx=ast.Load(),
                        ),
                        attr=method_name,
                        ctx=ast.Load(),
                    )
                )
            ],
            decorator_list=[],
        )

        # Add the method to the class (after __init__)
        # Find the position after __init__
        insert_position = 0
        for i, item in enumerate(class_node.body):
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                insert_position = i + 1
                break

        class_node.body.insert(insert_position, method_def)
