"""Replace Data Value with Object refactoring - turn a primitive value into an object."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class ReplaceDataValueWithObject(RefactoringBase):
    """Replace a primitive data value with an object (Value Object pattern)."""

    def __init__(self, file_path: str, target: str, name: str):
        """Initialize the ReplaceDataValueWithObject refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field to replace (e.g., "Order::customer")
            name: Name of the new value object class (e.g., "Customer")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.new_class_name = name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the replace data value with object refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new value object class
        """
        self.source = source

        if "::" not in self.target:
            raise ValueError(
                f"Target must be in format 'ClassName::field_name', got '{self.target}'"
            )

        class_name, field_name = self.target.split("::", 1)

        # Parse the source code
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class
        class_node = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                class_node = node
                break

        if class_node is None:
            raise ValueError(f"Class '{class_name}' not found in {self.file_path}")

        # Step 1: Create the new value object class
        new_class = self._create_value_object_class(field_name)

        # Step 2: Update the target class to use the new value object
        self._update_class_to_use_value_object(class_node, field_name)

        # Step 3: Insert the new class before the target class
        class_index = tree.body.index(class_node)
        tree.body.insert(class_index, new_class)

        # Fix missing location information in the AST
        ast.fix_missing_locations(tree)

        # Unparse the modified AST back to source code
        refactored = ast.unparse(tree)
        return refactored

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        if "::" not in self.target:
            return False
        class_name, field_name = self.target.split("::", 1)
        return class_name in source and field_name in source

    def _create_value_object_class(self, field_name: str) -> ast.ClassDef:
        """Create a new value object class.

        Args:
            field_name: Name of the field (used to derive parameter name)

        Returns:
            AST ClassDef node for the new value object
        """
        # Derive parameter name from field name (e.g., "customer" -> "name", or use singular form)
        # For simplicity, if field is "customer", use "name" as the parameter
        param_name = "name"

        # Create __init__ method: def __init__(self, name):
        init_method = ast.FunctionDef(
            name="__init__",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self", annotation=None),
                    ast.arg(arg=param_name, annotation=None),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[
                ast.Assign(
                    targets=[
                        ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr=param_name,
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Name(id=param_name, ctx=ast.Load()),
                )
            ],
            decorator_list=[],
            returns=None,
        )

        # Create the class
        class_def = ast.ClassDef(
            name=self.new_class_name,
            bases=[],
            keywords=[],
            body=[init_method],
            decorator_list=[],
        )

        return class_def

    def _update_class_to_use_value_object(self, class_node: ast.ClassDef, field_name: str) -> None:
        """Update the target class to use the new value object.

        Args:
            class_node: The AST ClassDef node of the target class
            field_name: Name of the field being replaced
        """
        # Store the original parameter name from __init__
        original_param_name = None

        # Step 1: Update __init__ to create an instance of the new class
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                # Extract the parameter name used for this field
                for node in item.body:
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                                and target.attr == field_name
                            ):
                                # Get the original parameter name
                                if isinstance(node.value, ast.Name):
                                    original_param_name = node.value.id

                                # Replace the assignment value with NewClass(param)
                                node.value = ast.Call(
                                    func=ast.Name(id=self.new_class_name, ctx=ast.Load()),
                                    args=[
                                        ast.Name(
                                            id=original_param_name
                                            if original_param_name
                                            else field_name,
                                            ctx=ast.Load(),
                                        )
                                    ],
                                    keywords=[],
                                )

        # Step 2: Update return statements in other methods
        # Update methods that return the field value to return field.name instead
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name != "__init__":
                # Walk through return statements
                for node in ast.walk(item):
                    if isinstance(node, ast.Return):
                        if node.value and isinstance(node.value, ast.Attribute):
                            if (
                                isinstance(node.value.value, ast.Name)
                                and node.value.value.id == "self"
                                and node.value.attr == field_name
                            ):
                                # Update return self.field_name to return self.field_name.name
                                node.value = ast.Attribute(
                                    value=ast.Attribute(
                                        value=ast.Name(id="self", ctx=ast.Load()),
                                        attr=field_name,
                                        ctx=ast.Load(),
                                    ),
                                    attr="name",
                                    ctx=ast.Load(),
                                )
