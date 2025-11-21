"""Extract Class refactoring - extract fields and methods into a new class."""

import ast
import copy
import re
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class ExtractClass(RefactoringBase):
    """Extract a subset of fields and methods from a class into a new class."""

    def __init__(
        self,
        file_path: str,
        source: str,
        fields: str,
        methods: str,
        name: str,
    ):
        """Initialize the ExtractClass refactoring.

        Args:
            file_path: Path to the Python file to refactor
            source: Source class name to extract from
            fields: Comma-separated list of field names to extract
            methods: Comma-separated list of method names to extract
            name: Name of the new class to create
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.source_class = source
        self.fields_to_move = [f.strip() for f in fields.split(",")]
        self.methods_to_move = [m.strip() for m in methods.split(",")]
        self.new_class_name = name

    def apply(self, source: str) -> str:
        """Apply the extract class refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new class created
        """
        # Parse the source code
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the source class
        source_class_node = self.find_class_def(tree, self.source_class)
        if not source_class_node:
            raise ValueError(f"Source class '{self.source_class}' not found")

        # Extract field assignments and methods
        field_assignments = []
        methods = []

        # Find __init__ method
        init_method = None
        for item in source_class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method:
            # Extract field assignments
            for field_name in self.fields_to_move:
                for stmt in init_method.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if (
                                    isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                    and target.attr == field_name
                                ):
                                    field_assignments.append((field_name, stmt))

        # Extract methods
        for method_name in self.methods_to_move:
            for item in source_class_node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    methods.append((method_name, item))

        # Create the new class
        new_class = self._create_new_class(field_assignments, methods)

        # Update the source class
        self._update_source_class(source_class_node, field_assignments, methods, init_method)

        # Find the index of the source class and insert new class after it
        source_class_index = None
        for i, node in enumerate(tree.body):
            if isinstance(node, ast.ClassDef) and node.name == self.source_class:
                source_class_index = i
                break

        if source_class_index is not None:
            tree.body.insert(source_class_index + 1, new_class)

        # Fix missing locations
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

            # Check that the source class exists
            source_class = self.find_class_def(tree, self.source_class)
            if not source_class:
                return False

            # Check that all fields exist in __init__
            init_method = None
            for item in source_class.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    init_method = item
                    break

            if init_method:
                for field_name in self.fields_to_move:
                    found = False
                    for stmt in init_method.body:
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if isinstance(target, ast.Attribute):
                                    if (
                                        isinstance(target.value, ast.Name)
                                        and target.value.id == "self"
                                        and target.attr == field_name
                                    ):
                                        found = True
                    if not found:
                        return False

            # Check that all methods exist
            for method_name in self.methods_to_move:
                found = False
                for item in source_class.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        found = True
                if not found:
                    return False

            return True
        except (SyntaxError, AttributeError, ValueError):
            return False

    def _create_new_class(self, field_assignments, methods):
        """Create a new class with extracted fields and methods.

        Args:
            field_assignments: List of (field_name, assignment_stmt) tuples
            methods: List of (method_name, method_node) tuples

        Returns:
            A ClassDef AST node for the new class
        """
        # Create __init__ for new class
        init_args = [ast.arg(arg="self", annotation=None)]
        init_body = []

        # Map old field names to new field names (remove prefix if present)
        field_mappings = {}
        for field_name, _ in field_assignments:
            new_field_name = self._extract_field_name(field_name)
            field_mappings[field_name] = new_field_name
            # Create assignment: self.new_name = new_name
            init_args.append(ast.arg(arg=new_field_name, annotation=None))
            init_body.append(
                ast.Assign(
                    targets=[
                        ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Store()),
                            attr=new_field_name,
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Name(id=new_field_name, ctx=ast.Load()),
                )
            )

        # Create __init__ method
        init_method = ast.FunctionDef(
            name="__init__",
            args=ast.arguments(
                posonlyargs=[],
                args=init_args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=init_body if init_body else [ast.Pass()],
            decorator_list=[],
            returns=None,
        )

        # Copy and update methods
        class_body = [init_method]
        for method_name, method_node in methods:
            # Deep copy the method
            method_copy = copy.deepcopy(method_node)
            # Update field references in the method
            self._update_field_refs_in_method(method_copy, field_mappings)
            class_body.append(method_copy)

        # Create the new class
        new_class = ast.ClassDef(
            name=self.new_class_name,
            bases=[],
            keywords=[],
            body=class_body,
            decorator_list=[],
        )

        return new_class

    def _update_source_class(self, source_class, field_assignments, methods, init_method):
        """Update the source class to use the new class.

        Args:
            source_class: The source ClassDef node
            field_assignments: List of (field_name, assignment_stmt) tuples
            methods: List of (method_name, method_node) tuples
            init_method: The __init__ method of the source class
        """
        # Remove field assignments from __init__
        if init_method:
            for field_name, stmt in field_assignments:
                if stmt in init_method.body:
                    init_method.body.remove(stmt)

        # Create field name for new class instance based on prefix
        new_class_field_name = self._derive_new_class_field_name(field_assignments)

        # Add new class instance to __init__
        if init_method:
            # Create arguments for new class instantiation using field names
            init_args = []
            for field_name, _ in field_assignments:
                # Pass the field name as it appears in __init__ parameters
                init_args.append(ast.Name(id=field_name, ctx=ast.Load()))

            # Add assignment of new class instance
            new_class_instance = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Store()),
                        attr=new_class_field_name,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Call(
                    func=ast.Name(id=self.new_class_name, ctx=ast.Load()),
                    args=init_args,
                    keywords=[],
                ),
            )
            # Insert after other field initializations
            init_method.body.insert(len(init_method.body), new_class_instance)

        # Remove extracted methods from source class
        methods_to_remove = []
        for item in source_class.body:
            if isinstance(item, ast.FunctionDef):
                for method_name, _ in methods:
                    if item.name == method_name:
                        methods_to_remove.append(item)

        for method in methods_to_remove:
            source_class.body.remove(method)

        # Add delegation methods to source class
        for method_name, method_node in methods:
            delegation_method = self._create_delegation_method(method_name, new_class_field_name)
            source_class.body.append(delegation_method)

    def _create_delegation_method(self, method_name: str, new_class_field_name: str):
        """Create a delegation method that calls the new class.

        Args:
            method_name: Name of the method
            new_class_field_name: Name of the field holding the new class instance

        Returns:
            A FunctionDef AST node for the delegation method
        """
        # Create: return self.new_class_field.method_name()
        delegation = ast.Return(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=new_class_field_name,
                        ctx=ast.Load(),
                    ),
                    attr=method_name,
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            )
        )

        delegation_method = ast.FunctionDef(
            name=method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self", annotation=None)],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[delegation],
            decorator_list=[],
            returns=None,
        )

        return delegation_method

    def _update_field_refs_in_method(self, method_node, field_mappings):
        """Update field references in a method to use new field names.

        Args:
            method_node: The FunctionDef AST node
            field_mappings: Dict mapping old field names to new field names
        """
        for node in ast.walk(method_node):
            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "self"
                    and node.attr in field_mappings
                ):
                    node.attr = field_mappings[node.attr]

    def _derive_new_class_field_name(self, field_assignments):
        """Derive the field name for the new class instance.

        Extracts common prefix from field names and combines with new class name.
        E.g., ["office_area_code", "office_number"] with "TelephoneNumber" -> "office_telephone"

        Args:
            field_assignments: List of (field_name, assignment_stmt) tuples

        Returns:
            The field name for holding the new class instance
        """
        if not field_assignments:
            return self._camel_to_snake(self.new_class_name)

        # Find common prefix among field names
        field_names = [f[0] for f in field_assignments]
        common_prefix = ""

        if len(field_names) > 0:
            # Find the common prefix
            for i, char in enumerate(field_names[0]):
                if all(i < len(name) and name[i] == char for name in field_names):
                    common_prefix += char
                else:
                    break

            # Trim to the last underscore or complete word
            if "_" in common_prefix:
                common_prefix = common_prefix[: common_prefix.rfind("_") + 1]
            else:
                common_prefix = ""

        # Combine prefix with lowercase first word of new class name
        # E.g., TelephoneNumber -> telephone
        new_class_word = self._first_word_of_camel_case(self.new_class_name)
        return common_prefix + new_class_word

    def _extract_field_name(self, field_name: str) -> str:
        """Extract field name by removing common prefixes.

        Args:
            field_name: The original field name (e.g., "office_area_code")

        Returns:
            The extracted field name (e.g., "area_code")
        """
        # Common prefixes to remove
        prefixes = ["office_", "get_", "set_"]
        for prefix in prefixes:
            if field_name.startswith(prefix):
                return field_name[len(prefix) :]
        return field_name

    def _first_word_of_camel_case(self, name: str) -> str:
        """Extract the first word from CamelCase and convert to lowercase.

        Args:
            name: The CamelCase name (e.g., "TelephoneNumber")

        Returns:
            The first word in lowercase (e.g., "telephone")
        """
        # Find the position of the first uppercase letter after the initial one
        for i in range(1, len(name)):
            if name[i].isupper():
                return name[:i].lower()
        # If no second uppercase letter, return the whole name in lowercase
        return name.lower()

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case.

        Args:
            name: The CamelCase name

        Returns:
            The snake_case name
        """
        # Insert underscore before uppercase letters (except the first one)
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        # Insert underscore before uppercase letters in acronyms
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
