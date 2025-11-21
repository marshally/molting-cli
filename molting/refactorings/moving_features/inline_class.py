"""Inline Class refactoring - move all features from one class into another."""

import ast
import copy
import re
from pathlib import Path
from typing import Optional

from molting.core.refactoring_base import RefactoringBase


class InlineClass(RefactoringBase):
    """Inline a class that isn't doing very much back into another class."""

    def __init__(self, file_path: str, source_class: str, into: str, field_prefix: str = ""):
        """Initialize the InlineClass refactoring.

        Args:
            file_path: Path to the Python file to refactor
            source_class: Class to inline (e.g., "TelephoneNumber")
            into: Class to inline into (e.g., "Person")
            field_prefix: Optional prefix for inlined fields (e.g., "office_")
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.source_class = source_class
        self.into_class = into
        self.field_prefix = field_prefix

    def apply(self, source: str) -> str:
        """Apply the inline class refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with class inlined
        """
        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the source class and destination class
        source_class_node = None
        dest_class_node = None

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name == self.source_class:
                    source_class_node = node
                elif node.name == self.into_class:
                    dest_class_node = node

        if not source_class_node:
            raise ValueError(f"Source class '{self.source_class}' not found")
        if not dest_class_node:
            raise ValueError(f"Destination class '{self.into_class}' not found")

        # If no prefix is provided, infer it from the field that holds the source class instance
        if not self.field_prefix:
            self.field_prefix = self._infer_field_prefix(dest_class_node, self.source_class)

        # Inline the class
        self._inline_class(tree, dest_class_node, source_class_node)

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
            tree = ast.parse(source)

            source_class = None
            dest_class = None

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name == self.source_class:
                        source_class = node
                    elif node.name == self.into_class:
                        dest_class = node

            if not source_class or not dest_class:
                return False

            return True
        except (SyntaxError, AttributeError, ValueError):
            return False

    def _infer_field_prefix(self, dest_class_node: ast.ClassDef, source_class_name: str) -> str:
        """Infer the field prefix from the field holding the source class instance.

        Args:
            dest_class_node: The destination class node
            source_class_name: The name of the source class

        Returns:
            The inferred prefix (e.g., "office_")
        """
        # Find __init__ method
        for item in dest_class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                # Look for assignments of source class instances
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if isinstance(target.value, ast.Name) and target.value.id == "self":
                                    # Check if value is creating an instance of source class
                                    if isinstance(stmt.value, ast.Call):
                                        if isinstance(stmt.value.func, ast.Name):
                                            if stmt.value.func.id == source_class_name:
                                                # Found it! Return field name with trailing underscore
                                                field_name = target.attr
                                                # Remove trailing part after any common suffix
                                                # e.g., "office_telephone" -> "office_"
                                                prefix = re.sub(r"_\w+$", "_", field_name)
                                                if prefix == field_name:
                                                    # No common suffix found, use field name as prefix
                                                    prefix = field_name + "_"
                                                return prefix
        return ""

    def _inline_class(
        self,
        tree: ast.Module,
        dest_class_node: ast.ClassDef,
        source_class_node: ast.ClassDef,
    ):
        """Inline all features from source class into destination class.

        Args:
            tree: The AST module
            dest_class_node: The destination class node
            source_class_node: The source class node to inline
        """
        # Get fields from source class __init__
        source_fields = self._extract_fields(source_class_node)

        # Get methods from source class (excluding __init__)
        source_methods = [
            item
            for item in source_class_node.body
            if isinstance(item, ast.FunctionDef) and item.name != "__init__"
        ]

        # Create mapping of source method names to their bodies
        method_bodies = {}
        for method_node in source_methods:
            method_bodies[method_node.name] = method_node

        # Find the field in destination class that holds the source class instance
        instance_field_name = self._find_instance_field(dest_class_node, self.source_class)

        # Track which methods were replaced with delegating calls
        replaced_method_names = set()

        # Update delegating method calls BEFORE removing the instance field
        if instance_field_name:
            replaced_method_names = self._replace_delegating_calls(
                dest_class_node, instance_field_name, method_bodies
            )

        # Remove the instance field from destination class
        if instance_field_name:
            self._remove_field_from_class(dest_class_node, instance_field_name)

        # Add source class fields to destination class with prefix
        for field_name, field_assignment in source_fields:
            prefixed_field_name = self.field_prefix + field_name
            prefixed_assignment = copy.deepcopy(field_assignment)

            # Update the assignment target to use prefixed name
            if isinstance(prefixed_assignment, ast.Assign):
                for target in prefixed_assignment.targets:
                    if isinstance(target, ast.Attribute):
                        target.attr = prefixed_field_name

            self._add_field_to_class(dest_class_node, prefixed_assignment)

        # Add source class methods to destination class
        # UNLESS they were already inlined into existing delegating methods
        for method_node in source_methods:
            if method_node.name not in replaced_method_names:
                # Update method to use prefixed field names
                self._update_method_references(method_node, source_fields)
                method_copy = copy.deepcopy(method_node)
                self._add_method_to_class(dest_class_node, method_copy)

        # Remove the source class from the tree
        tree.body = [
            node
            for node in tree.body
            if not (isinstance(node, ast.ClassDef) and node.name == self.source_class)
        ]

    def _extract_fields(self, class_node: ast.ClassDef) -> list:
        """Extract fields from a class __init__ method.

        Args:
            class_node: The ClassDef AST node

        Returns:
            List of (field_name, assignment_stmt) tuples
        """
        fields = []
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if isinstance(target.value, ast.Name) and target.value.id == "self":
                                    fields.append((target.attr, stmt))
        return fields

    def _find_instance_field(
        self, class_node: ast.ClassDef, source_class_name: str
    ) -> Optional[str]:
        """Find the field that holds an instance of the source class.

        Args:
            class_node: The class node to search
            source_class_name: The name of the source class

        Returns:
            The field name or None if not found
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if isinstance(target.value, ast.Name) and target.value.id == "self":
                                    # Check if value is creating an instance of source class
                                    if isinstance(stmt.value, ast.Call):
                                        if isinstance(stmt.value.func, ast.Name):
                                            if stmt.value.func.id == source_class_name:
                                                return target.attr
        return None

    def _remove_field_from_class(self, class_node: ast.ClassDef, field_name: str):
        """Remove a field from a class __init__ method.

        Args:
            class_node: The class node
            field_name: The name of the field to remove
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                # Find and remove the field assignment
                to_remove = None
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if isinstance(target.value, ast.Name) and target.value.id == "self":
                                    if target.attr == field_name:
                                        to_remove = stmt
                                        break
                if to_remove:
                    item.body.remove(to_remove)

    def _add_field_to_class(self, class_node: ast.ClassDef, field_assignment: ast.stmt):
        """Add a field assignment to a class __init__ method.

        Args:
            class_node: The class node
            field_assignment: The assignment statement to add
        """
        # Find or create __init__ method
        init_method = None
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method is None:
            # Create __init__ method
            init_method = ast.FunctionDef(
                name="__init__",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self", annotation=None)],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[field_assignment],
                decorator_list=[],
                returns=None,
            )
            class_node.body.insert(0, init_method)
        else:
            # Add to existing __init__
            init_method.body.append(field_assignment)

    def _add_method_to_class(self, class_node: ast.ClassDef, method_node: ast.FunctionDef):
        """Add a method to a class.

        Args:
            class_node: The class node
            method_node: The method to add
        """
        class_node.body.append(method_node)

    def _update_method_references(
        self, method_node: ast.FunctionDef, source_fields: list[tuple[str, ast.stmt]]
    ):
        """Update field references in a method to use prefixed names.

        Args:
            method_node: The method node
            source_fields: List of (field_name, assignment) tuples from source class
        """
        field_names = [name for name, _ in source_fields]

        # Walk through the method and replace references
        for node in ast.walk(method_node):
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id == "self":
                    if node.attr in field_names:
                        # Replace with prefixed name
                        node.attr = self.field_prefix + node.attr

    def _replace_delegating_calls(
        self,
        dest_class_node: ast.ClassDef,
        instance_field_name: str,
        method_bodies: dict,
    ) -> set[str]:
        """Replace delegating method calls with inlined method bodies.

        Replaces methods like:
            def get_telephone_number(self):
                return self.office_telephone.get_telephone_number()

        With the inlined method body (with fields prefixed).

        Args:
            dest_class_node: The destination class node
            instance_field_name: The field name holding the source class instance
            method_bodies: Dict mapping method names to their AST nodes

        Returns:
            Set of method names that were replaced with inlined bodies
        """
        replaced_methods = set()

        # Find methods in dest_class that delegate to instance_field
        for item in dest_class_node.body:
            if isinstance(item, ast.FunctionDef):
                # Check if this is a single-statement method with a return
                if len(item.body) == 1:
                    stmt = item.body[0]
                    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        # Check for pattern: self.instance_field.method_name()
                        if isinstance(call.func, ast.Attribute):
                            if isinstance(call.func.value, ast.Attribute):
                                attr = call.func.value
                                if isinstance(attr.value, ast.Name):
                                    if (
                                        attr.value.id == "self"
                                        and attr.attr == instance_field_name
                                        and call.func.attr in method_bodies
                                    ):
                                        # This method delegates to the inlined class
                                        # Replace its body with the inlined method body
                                        source_method = method_bodies[call.func.attr]
                                        new_body = copy.deepcopy(source_method.body)

                                        # Update field references in the copied body to use prefixes
                                        self._prefix_field_references_in_body(new_body)

                                        item.body = new_body
                                        replaced_methods.add(call.func.attr)

        return replaced_methods

    def _prefix_field_references_in_body(self, body: list[ast.stmt]):
        """Prefix all field references in a method body.

        Updates references like self.area_code to self.office_area_code

        Args:
            body: List of statements in the method body
        """
        # Walk through all nodes in the body and update field references
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) and node.value.id == "self":
                        # This is a self.field reference - add prefix if not already prefixed
                        if not node.attr.startswith(self.field_prefix):
                            node.attr = self.field_prefix + node.attr
