"""Replace Type Code with Class refactoring - turn type codes into class instances."""

import ast
from pathlib import Path
from typing import Any, Optional

from molting.core.refactoring_base import RefactoringBase


class ReplaceTypeCodeWithClass(RefactoringBase):
    """Replace a type code (int/string constants) with instances of a class."""

    def __init__(self, file_path: str, target: str, name: str):
        """Initialize the ReplaceTypeCodeWithClass refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field to replace (e.g., "Person::blood_group")
            name: Name of the new class to create (e.g., "BloodGroup")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.new_class_name = name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the replace type code with class refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new type class
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
        class_index: Optional[int] = None
        for idx, node in enumerate(tree.body):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                class_node = node
                class_index = idx
                break

        if class_node is None or class_index is None:
            raise ValueError(f"Class '{class_name}' not found in {self.file_path}")

        # Extract type code constants from the class
        type_codes = self._extract_type_codes(class_node)

        if not type_codes:
            raise ValueError(f"No type code constants found in class '{class_name}'")

        # Create the new type code class
        new_class = self._create_type_code_class(type_codes)

        # Update the target class to remove type codes
        self._remove_type_codes(class_node)

        # Insert the new class before the target class
        tree.body.insert(class_index, new_class)

        # Add assignments for type code instances after the new class
        assignment_stmts = self._create_type_code_assignments(type_codes)
        for i, stmt in enumerate(assignment_stmts):
            tree.body.insert(class_index + 1 + i, stmt)

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

    def _extract_type_codes(
        self, class_node: ast.ClassDef
    ) -> dict[str, Any]:
        """Extract type code constants from the class.

        Args:
            class_node: The AST ClassDef node of the target class

        Returns:
            Dictionary mapping constant names to their values
        """
        type_codes: dict[str, Any] = {}

        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Extract the value
                        if isinstance(node.value, ast.Constant):
                            type_codes[target.id] = node.value.value
                        elif isinstance(node.value, ast.Num):
                            type_codes[target.id] = node.value.n

        return type_codes

    def _create_type_code_class(
        self, type_codes: dict[str, Any]
    ) -> ast.ClassDef:
        """Create a new type code class.

        Args:
            type_codes: Dictionary mapping constant names to their values

        Returns:
            AST ClassDef node for the new type code class
        """
        # Create __init__ method: def __init__(self, code):
        init_method = ast.FunctionDef(
            name="__init__",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self", annotation=None),
                    ast.arg(arg="code", annotation=None),
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
                            attr="_code",
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Name(id="code", ctx=ast.Load()),
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

    def _remove_type_codes(self, class_node: ast.ClassDef) -> None:
        """Remove type code constants from the class.

        Args:
            class_node: The AST ClassDef node of the target class
        """
        nodes_to_remove = []
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.isupper():
                            nodes_to_remove.append(node)
                            break

        for node in nodes_to_remove:
            class_node.body.remove(node)

    def _create_type_code_assignments(
        self, type_codes: dict[str, Any]
    ) -> list[ast.Assign]:
        """Create assignment statements for type code instances.

        Args:
            type_codes: Dictionary mapping constant names to their values

        Returns:
            List of AST assignment statements
        """
        assignments = []

        for const_name, value in type_codes.items():
            assignment = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id=self.new_class_name, ctx=ast.Load()),
                        attr=const_name,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Call(
                    func=ast.Name(id=self.new_class_name, ctx=ast.Load()),
                    args=[ast.Constant(value=value)],
                    keywords=[],
                ),
            )
            assignments.append(assignment)

        return assignments
