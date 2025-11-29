"""Change Reference to Value refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ChangeReferenceToValueCommand(BaseCommand):
    """Convert a reference object to a value object.

    The Change Reference to Value refactoring transforms a class that is
    currently treated as a reference object (identity-based, mutable) into a
    value object (equality-based, immutable). This makes the class immutable
    and implements __eq__ and __hash__ methods based on the object's data
    rather than its identity.

    **When to use:**
    - The object is small and rarely changes, making immutability practical
    - You want to use the object as a dictionary key or in sets
    - Objects are frequently copied or passed around the system
    - You want to simplify equality comparisons based on content rather than identity
    - The class currently uses a registry pattern (like a classmethod "get") that
      you want to eliminate

    **Example:**
    Before:
        class Currency:
            _instances = {}

            def __init__(self, code):
                self.code = code

            @classmethod
            def get(cls, code):
                if code not in cls._instances:
                    cls._instances[code] = Currency(code)
                return cls._instances[code]

    After:
        class Currency:
            def __init__(self, code):
                self.code = code

            def __eq__(self, other):
                if not isinstance(other, Currency):
                    return False
                return self.code == other.code

            def __hash__(self):
                return hash(self.code)
    """

    name = "change-reference-to-value"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply change-reference-to-value refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ChangeReferenceToValueTransformer(target)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ChangeReferenceToValueTransformer(cst.CSTTransformer):
    """Transforms a reference object into a value object."""

    def __init__(self, class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to transform
        """
        self.class_name = class_name
        self.init_params: list[str] = []

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform the class from reference to value object."""
        if updated_node.name.value != self.class_name:
            return updated_node

        # First pass: extract init parameters
        self._extract_init_params(updated_node)

        # Second pass: transform the class body
        new_body: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                # Keep __init__ as is
                if stmt.name.value == "__init__":
                    new_body.append(stmt)
                # Remove the class method (get)
                elif self._is_classmethod(stmt):
                    continue
            elif isinstance(stmt, cst.SimpleStatementLine):
                # Remove class variable _instances
                if self._is_instances_variable(stmt):
                    continue
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # Add __eq__ method
        new_body.append(self._create_eq_method())
        # Add __hash__ method
        new_body.append(self._create_hash_method())

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _extract_init_params(self, class_def: cst.ClassDef) -> None:
        """Extract parameter names from __init__ method.

        Args:
            class_def: The class definition to analyze
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                for param in stmt.params.params:
                    if param.name.value != "self":
                        self.init_params.append(param.name.value)
                break

    def _is_classmethod(self, func_def: cst.FunctionDef) -> bool:
        """Check if a function has a @classmethod decorator.

        Args:
            func_def: The function definition to check

        Returns:
            True if the function has @classmethod decorator
        """
        for decorator in func_def.decorators:
            if isinstance(decorator.decorator, cst.Name):
                if decorator.decorator.value == "classmethod":
                    return True
        return False

    def _is_instances_variable(self, stmt: cst.SimpleStatementLine) -> bool:
        """Check if statement is the _instances class variable.

        Args:
            stmt: The statement to check

        Returns:
            True if it's the _instances variable assignment
        """
        for body_item in stmt.body:
            if isinstance(body_item, cst.Assign):
                for target in body_item.targets:
                    if isinstance(target.target, cst.Name):
                        if target.target.value == "_instances":
                            return True
        return False

    def _create_eq_method(self) -> cst.FunctionDef:
        """Create the __eq__ method for value object semantics.

        Returns:
            The __eq__ method definition
        """
        # Build the comparison expression
        if not self.init_params:
            # If no params found, use a default attribute name
            comparison = cst.parse_expression("self.code == other.code")
        else:
            # Use the first parameter as the comparison field
            param_name = self.init_params[0]
            comparison = cst.parse_expression(f"self.{param_name} == other.{param_name}")

        body_stmts: list[cst.BaseStatement] = [
            # if not isinstance(other, Currency):
            cst.If(
                test=cst.UnaryOperation(
                    operator=cst.Not(),
                    expression=cst.Call(
                        func=cst.Name("isinstance"),
                        args=[
                            cst.Arg(value=cst.Name("other")),
                            cst.Arg(value=cst.Name(self.class_name)),
                        ],
                    ),
                ),
                body=cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("False"))])]
                ),
            ),
            # return self.code == other.code
            cst.SimpleStatementLine(body=[cst.Return(value=comparison)]),
        ]

        return cst.FunctionDef(
            name=cst.Name("__eq__"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(name=cst.Name("other")),
                ]
            ),
            body=cst.IndentedBlock(body=body_stmts),
        )

    def _create_hash_method(self) -> cst.FunctionDef:
        """Create the __hash__ method for value object semantics.

        Returns:
            The __hash__ method definition
        """
        # Use the first parameter as the hash field
        if not self.init_params:
            hash_expr = cst.parse_expression("hash(self.code)")
        else:
            param_name = self.init_params[0]
            hash_expr = cst.parse_expression(f"hash(self.{param_name})")

        return cst.FunctionDef(
            name=cst.Name("__hash__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[cst.SimpleStatementLine(body=[cst.Return(value=hash_expr)])]
            ),
        )


# Register the command
register_command(ChangeReferenceToValueCommand)
