"""Move Field refactoring - move a field from one class to another."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class MoveField(RefactoringBase):
    """Move a field from one class to another using AST transformation."""

    def __init__(self, file_path: str, source: str, to: str):
        """Initialize the MoveField refactoring.

        Args:
            file_path: Path to the Python file to refactor
            source: Source field as "ClassName::field_name"
            to: Destination class name
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.source_spec = source
        self.to = to

    def apply(self, source: str) -> str:
        """Apply the move field refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with field moved to destination class
        """
        # Parse the source class and field name
        class_name, field_name = self.source_spec.split("::", 1)

        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the source class and destination class
        source_class = None
        dest_class = None

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name == class_name:
                    source_class = node
                elif node.name == self.to:
                    dest_class = node

        if not source_class:
            raise ValueError(f"Source class '{class_name}' not found")
        if not dest_class:
            raise ValueError(f"Destination class '{self.to}' not found")

        # Find and extract the field from the source class
        field_assignment, init_method = self._find_field_assignment_and_init(source_class, field_name)
        if not field_assignment:
            raise ValueError(f"Field '{field_name}' not found in class '{class_name}'")

        # Make a deep copy of the field assignment
        import copy
        field_assignment_copy = copy.deepcopy(field_assignment)

        # Remove the field from source class __init__
        init_method.body.remove(field_assignment)

        # Add the field to destination class, creating __init__ if needed
        self._add_field_to_class(dest_class, field_assignment_copy)

        # Convert class name to parameter name (snake_case)
        dest_attr_name = self._camel_to_snake(self.to)

        # Update references to the field in source class methods
        self._update_field_references(source_class, field_name, dest_attr_name)

        # Add destination class instance parameter to source class __init__
        self._add_destination_parameter(source_class, dest_attr_name)

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
            # Check that both the source class and destination class exist
            class_name, field_name = self.source_spec.split("::", 1)
            tree = ast.parse(source)

            source_class = None
            dest_class = None

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name == class_name:
                        source_class = node
                    elif node.name == self.to:
                        dest_class = node

            if not source_class or not dest_class:
                return False

            # Check that the field exists
            return self._find_field_assignment(source_class, field_name) is not None

        except (SyntaxError, AttributeError, ValueError):
            return False

    def _find_field_assignment(self, class_node: ast.ClassDef, field_name: str):
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
                                if (isinstance(target.value, ast.Name) and
                                    target.value.id == "self" and
                                    target.attr == field_name):
                                    return stmt
        return None

    def _find_field_assignment_and_init(self, class_node: ast.ClassDef, field_name: str):
        """Find a field assignment and its containing __init__ method.

        Args:
            class_node: The ClassDef AST node
            field_name: The name of the field

        Returns:
            Tuple of (assignment statement AST node, __init__ method AST node) or (None, None) if not found
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if (isinstance(target.value, ast.Name) and
                                    target.value.id == "self" and
                                    target.attr == field_name):
                                    return stmt, item
        return None, None

    def _add_field_to_class(self, class_node: ast.ClassDef, field_assignment: ast.stmt):
        """Add a field assignment to a class, creating __init__ if needed.

        Args:
            class_node: The ClassDef AST node
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
                    defaults=[]
                ),
                body=[field_assignment],
                decorator_list=[],
                returns=None
            )

            # Remove `pass` statements from class body and insert __init__ at start
            class_node.body = [
                item for item in class_node.body
                if not (isinstance(item, ast.Pass))
            ]
            class_node.body.insert(0, init_method)
        else:
            # Add to existing __init__
            init_method.body.append(field_assignment)

    def _update_field_references(self, class_node: ast.ClassDef, field_name: str,
                                  dest_attr_name: str):
        """Update references to a field in class methods.

        Args:
            class_node: The ClassDef AST node
            field_name: The name of the field
            dest_attr_name: The attribute name for the destination object (e.g., "accountType")
        """
        # Create a visitor to replace field references
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name != "__init__":
                # Skip __init__ since we handle it separately
                self._replace_in_node(item, field_name, dest_attr_name)

    def _replace_in_node(self, node, field_name: str, dest_attr_name: str):
        """Recursively replace field references in an AST node.

        Args:
            node: The AST node to search
            field_name: The name of the field to replace
            dest_attr_name: The attribute name for the destination object
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                if (isinstance(child.value, ast.Name) and
                    child.value.id == "self" and
                    child.attr == field_name):
                    # Replace self.field_name with self.dest_attr_name.field_name
                    child.value = ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=dest_attr_name,
                        ctx=ast.Load()
                    )
                    child.attr = field_name

    def _add_destination_parameter(self, class_node: ast.ClassDef, dest_attr_name: str):
        """Add a parameter for the destination object to the source class __init__.

        Args:
            class_node: The ClassDef AST node
            dest_attr_name: The attribute name for the destination object (e.g., "accountType")
        """
        # Find or create __init__ method
        init_method = None
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method is None:
            # Create __init__ with the parameter
            init_method = ast.FunctionDef(
                name="__init__",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[
                        ast.arg(arg="self", annotation=None),
                        ast.arg(arg=dest_attr_name, annotation=None)
                    ],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[]
                ),
                body=[
                    ast.Assign(
                        targets=[
                            ast.Attribute(
                                value=ast.Name(id="self", ctx=ast.Store()),
                                attr=dest_attr_name,
                                ctx=ast.Store()
                            )
                        ],
                        value=ast.Name(id=dest_attr_name, ctx=ast.Load())
                    )
                ],
                decorator_list=[],
                returns=None
            )
            class_node.body.insert(0, init_method)
        else:
            # Add parameter to existing __init__
            init_method.args.args.append(ast.arg(arg=dest_attr_name, annotation=None))

            # Add assignment at the beginning of __init__
            assignment = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Store()),
                        attr=dest_attr_name,
                        ctx=ast.Store()
                    )
                ],
                value=ast.Name(id=dest_attr_name, ctx=ast.Load())
            )
            init_method.body.insert(0, assignment)

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case.

        Args:
            name: The CamelCase name (e.g., "AccountType")

        Returns:
            The snake_case name (e.g., "account_type")
        """
        import re
        # Insert underscore before uppercase letters (except the first one)
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscore before uppercase letters in acronyms
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
