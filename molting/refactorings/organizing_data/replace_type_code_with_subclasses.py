"""Replace Type Code with Subclasses refactoring - replace type codes with inheritance hierarchy."""

import ast
from pathlib import Path
from typing import List, Optional

from molting.core.refactoring_base import RefactoringBase


class ReplaceTypeCodeWithSubclasses(RefactoringBase):
    """Replace type codes with subclasses.

    Transforms code that uses type codes (like integer constants) into a proper
    inheritance hierarchy where each type code becomes a subclass.
    """

    def __init__(self, file_path: str, target: str, type_field: Optional[str] = None):
        """Initialize the ReplaceTypeCodeWithSubclasses refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field to replace (e.g., "Employee::type")
            type_field: Optional alternative parameter name for the type field
        """
        self.file_path = Path(file_path)
        self.target = target
        self.type_field = type_field
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the replace type code with subclasses refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with subclasses instead of type codes
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

        # Extract type codes from the class constants (maintaining order)
        type_codes = self._extract_type_codes(class_node, field_name)

        if not type_codes:
            raise ValueError(f"Could not find type code constants in class '{class_name}'")

        # Remove the __init__ method from the class
        self._remove_init_method(class_node)

        # Remove type code constants from the base class
        self._remove_type_code_constants(class_node)

        # Create a factory method
        self._add_factory_method(class_node, field_name, type_codes)

        # Create subclasses for each type code
        subclasses = self._create_subclasses(class_name, type_codes)

        # Find the index of the original class
        class_index = tree.body.index(class_node)

        # Insert subclasses after the base class
        for i, subclass in enumerate(subclasses, 1):
            tree.body.insert(class_index + i, subclass)

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

        # Check if class exists and has type code field
        try:
            tree = ast.parse(source)
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Check if class has the field in __init__
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            for assign in item.body:
                                if isinstance(assign, ast.Assign):
                                    for target in assign.targets:
                                        if (
                                            isinstance(target, ast.Attribute)
                                            and isinstance(target.value, ast.Name)
                                            and target.value.id == "self"
                                            and target.attr == field_name
                                        ):
                                            return True
            return False
        except SyntaxError:
            return False

    def _extract_type_codes(self, class_node: ast.ClassDef, field_name: str) -> List[str]:
        """Extract type code constants from the class in order.

        Args:
            class_node: The AST ClassDef node of the target class
            field_name: Name of the type field

        Returns:
            List of type constant names in order they appear
        """
        type_codes = []

        for item in class_node.body:
            # Look for class constants (Assign statements at class level)
            if isinstance(item, ast.Assign):
                # Check if this is a simple constant assignment
                if len(item.targets) == 1:
                    target = item.targets[0]
                    if isinstance(target, ast.Name):
                        # Extract the constant name
                        const_name = target.id

                        # Only collect uppercase constants (convention for type codes)
                        if const_name.isupper():
                            type_codes.append(const_name)

        return type_codes

    def _add_factory_method(
        self, class_node: ast.ClassDef, field_name: str, type_codes: List[str]
    ) -> None:
        """Add a factory method to create instances of the appropriate subclass.

        Args:
            class_node: The AST ClassDef node of the target class
            field_name: Name of the type field
            type_codes: List of type constant names in order
        """
        # Create the if-elif chain for the factory method
        conditions = []

        for type_name in type_codes:
            # Create condition: if employee_type == "ENGINEER"
            test = ast.Compare(
                left=ast.Name(id="employee_type", ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=type_name)],
            )

            # Create return statement: return Engineer()
            subclass_name = self._type_name_to_class_name(type_name)
            body = [
                ast.Return(
                    value=ast.Call(
                        func=ast.Name(id=subclass_name, ctx=ast.Load()), args=[], keywords=[]
                    )
                )
            ]

            conditions.append((test, body))

        # Build the if-elif chain
        orelse_chain = None
        for test, body in reversed(conditions):
            if orelse_chain is None:
                orelse_chain = ast.If(test=test, body=body, orelse=[])
            else:
                orelse_chain = ast.If(test=test, body=body, orelse=[orelse_chain])

        # Create the factory method
        factory_method = ast.FunctionDef(
            name="create",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="employee_type", annotation=None),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[orelse_chain] if orelse_chain else [ast.Pass()],
            decorator_list=[ast.Name(id="staticmethod", ctx=ast.Load())],
            returns=None,
        )

        # Insert the factory method at the beginning of the class
        class_node.body.insert(0, factory_method)

    def _create_subclasses(self, base_class_name: str, type_codes: List[str]) -> list:
        """Create subclasses for each type code.

        Args:
            base_class_name: Name of the base class
            type_codes: List of type constant names in order

        Returns:
            List of AST ClassDef nodes for the subclasses
        """
        subclasses = []

        for type_name in type_codes:
            subclass_name = self._type_name_to_class_name(type_name)

            # Create: class Engineer(Employee): pass
            subclass = ast.ClassDef(
                name=subclass_name,
                bases=[ast.Name(id=base_class_name, ctx=ast.Load())],
                keywords=[],
                body=[ast.Pass()],
                decorator_list=[],
            )

            subclasses.append(subclass)

        return subclasses

    def _remove_init_method(self, class_node: ast.ClassDef) -> None:
        """Remove __init__ method from the class.

        Args:
            class_node: The AST ClassDef node of the target class
        """
        items_to_remove = []

        for i, item in enumerate(class_node.body):
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                items_to_remove.append(i)

        # Remove in reverse order to maintain indices
        for i in reversed(items_to_remove):
            del class_node.body[i]

    def _remove_type_code_constants(self, class_node: ast.ClassDef) -> None:
        """Remove type code constant definitions from the class.

        Args:
            class_node: The AST ClassDef node of the target class
        """
        # Find and remove uppercase constant assignments
        items_to_remove = []

        for i, item in enumerate(class_node.body):
            if isinstance(item, ast.Assign):
                if len(item.targets) == 1:
                    target = item.targets[0]
                    if isinstance(target, ast.Name) and target.id.isupper():
                        # Skip if it's the staticmethod decorator
                        items_to_remove.append(i)

        # Remove in reverse order to maintain indices
        for i in reversed(items_to_remove):
            del class_node.body[i]

    def _type_name_to_class_name(self, type_name: str) -> str:
        """Convert a type constant name to a class name.

        Args:
            type_name: The type constant name (e.g., "ENGINEER")

        Returns:
            The class name (e.g., "Engineer")
        """
        # Convert ENGINEER -> Engineer
        return type_name.capitalize()
