"""Self Encapsulate Field refactoring - make field private with getter/setter properties."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class SelfEncapsulateField(RefactoringBase):
    """Make field private and provide property-based getter/setter methods."""

    def __init__(self, file_path: str, target: str):
        """Initialize the SelfEncapsulateField refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field to self-encapsulate (e.g., "ClassName::field_name")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the self encapsulate field refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with self-encapsulated field
        """
        # Use the provided source code
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

        # Find and modify the class
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Apply self-encapsulation
                self._self_encapsulate_in_class(node, field_name)
                break
        else:
            raise ValueError(f"Class '{class_name}' not found in {self.file_path}")

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
        # For now, just check that the target exists in the source
        if "::" not in self.target:
            return False
        class_name, field_name = self.target.split("::", 1)
        return class_name in source and field_name in source

    def _self_encapsulate_in_class(self, class_node: ast.ClassDef, field_name: str) -> None:
        """Self-encapsulate a field in a class.

        Makes the field private and provides property-based getter/setter methods.
        Field accesses remain the same since properties work like attributes.

        Args:
            class_node: The AST ClassDef node to modify
            field_name: Name of the field to self-encapsulate
        """
        private_field_name = f"_{field_name}"

        # Step 1: Check if this field is already encapsulated (has @property)
        already_has_property = any(
            isinstance(item, ast.FunctionDef)
            and item.name == field_name
            and any(
                isinstance(dec, ast.Name) and dec.id == "property" for dec in item.decorator_list
            )
            for item in class_node.body
        )

        if already_has_property:
            # Field is already encapsulated, just ensure the __init__ uses private field
            for item in class_node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    for node in ast.walk(item):
                        if isinstance(node, ast.Attribute):
                            if (
                                isinstance(node.value, ast.Name)
                                and node.value.id == "self"
                                and node.attr == field_name
                            ):
                                node.attr = private_field_name
            return

        # Step 2: Rename the field to private in __init__
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                # Replace self.field_name with self._field_name
                for node in ast.walk(item):
                    if isinstance(node, ast.Attribute):
                        if (
                            isinstance(node.value, ast.Name)
                            and node.value.id == "self"
                            and node.attr == field_name
                        ):
                            node.attr = private_field_name

        # Step 3: Find the position to insert methods (after __init__ and any existing properties)
        last_property_pos = 0
        for i, item in enumerate(class_node.body):
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                last_property_pos = i + 1
            elif isinstance(item, ast.FunctionDef):
                # Check if it has @property or setter decorator
                if any(
                    isinstance(dec, ast.Name) and dec.id == "property"
                    for dec in item.decorator_list
                ) or any(
                    isinstance(dec, ast.Attribute)
                    and isinstance(dec.value, ast.Name)
                    and dec.attr == "setter"
                    for dec in item.decorator_list
                ):
                    last_property_pos = i + 1

        # Step 4: Create getter property
        getter = self._create_getter_method(field_name, private_field_name)

        # Step 5: Create setter property
        setter = self._create_setter_method(field_name, private_field_name)

        # Step 6: Insert getter and setter properties after last property
        class_node.body.insert(last_property_pos, getter)
        class_node.body.insert(last_property_pos + 1, setter)

    def _create_getter_method(self, field_name: str, private_field_name: str) -> ast.FunctionDef:
        """Create a getter property.

        Args:
            field_name: Name of the public property
            private_field_name: Name of the private field

        Returns:
            AST FunctionDef node for the getter property
        """
        # Create the function body: return self._field_name
        return_stmt = ast.Return(
            value=ast.Attribute(
                value=ast.Name(id="self", ctx=ast.Load()), attr=private_field_name, ctx=ast.Load()
            )
        )

        # Create the @property decorator
        property_decorator = ast.Name(id="property", ctx=ast.Load())

        # Create the function definition
        func_def = ast.FunctionDef(
            name=field_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self", annotation=None)],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[return_stmt],
            decorator_list=[property_decorator],
            returns=None,
        )

        return func_def

    def _create_setter_method(self, field_name: str, private_field_name: str) -> ast.FunctionDef:
        """Create a setter property.

        Args:
            field_name: Name of the public property
            private_field_name: Name of the private field

        Returns:
            AST FunctionDef node for the setter property
        """
        # Create the function body: self._field_name = value
        assign_stmt = ast.Assign(
            targets=[
                ast.Attribute(
                    value=ast.Name(id="self", ctx=ast.Load()),
                    attr=private_field_name,
                    ctx=ast.Store(),
                )
            ],
            value=ast.Name(id="value", ctx=ast.Load()),
        )

        # Create the @field_name.setter decorator
        setter_decorator = ast.Attribute(
            value=ast.Name(id=field_name, ctx=ast.Load()), attr="setter", ctx=ast.Load()
        )

        # Create the function definition
        func_def = ast.FunctionDef(
            name=field_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self", annotation=None), ast.arg(arg="value", annotation=None)],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[assign_stmt],
            decorator_list=[setter_decorator],
            returns=None,
        )

        return func_def
