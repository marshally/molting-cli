"""Remove Middle Man refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class RemoveMiddleManCommand(BaseCommand):
    """Command to remove middle man delegation from a class."""

    name = "remove-middle-man"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for remove-middle-man: 'target'")

    def execute(self) -> None:
        """Apply remove-middle-man refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target"]
        source_code = self.file_path.read_text()

        tree = cst.parse_module(source_code)
        transformer = RemoveMiddleManTransformer(target_class)
        modified_tree = tree.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class RemoveMiddleManTransformer(cst.CSTTransformer):
    """Transforms code by removing middle man delegation."""

    def __init__(self, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to process
        """
        self.target_class = target_class
        self.delegate_field: str | None = None
        self.delegation_methods: list[str] = []

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class definitions to remove middle man."""
        if original_node.name.value != self.target_class:
            return updated_node

        # First pass: identify delegate field and delegation methods
        self._identify_delegate_and_methods(original_node)

        # Second pass: transform the class
        new_body: list[Any] = []
        for item in updated_node.body.body:
            # Skip delegation methods
            if isinstance(item, cst.FunctionDef):
                if item.name.value in self.delegation_methods:
                    continue
            # Transform field assignments
            elif isinstance(item, cst.SimpleStatementLine):
                transformed = self._transform_field_assignment(item)
                if transformed is not None:
                    new_body.append(transformed)
                    continue

            new_body.append(item)

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _identify_delegate_and_methods(self, class_def: cst.ClassDef) -> None:
        """Identify the delegate field and delegation methods.

        Args:
            class_def: The class definition to analyze
        """
        # Find private field assignments in __init__
        for item in class_def.body.body:
            if isinstance(item, cst.FunctionDef) and item.name.value == "__init__":
                for stmt in item.body.body:
                    if isinstance(stmt, cst.SimpleStatementLine):
                        for expr in stmt.body:
                            if isinstance(expr, cst.Assign):
                                # Find self._field = value patterns
                                target = expr.targets[0].target
                                if isinstance(target, cst.Attribute):
                                    if (
                                        isinstance(target.value, cst.Name)
                                        and target.value.value == "self"
                                    ):
                                        field_name = target.attr.value
                                        if field_name.startswith("_"):
                                            self.delegate_field = field_name

        # Find delegation methods
        if self.delegate_field:
            public_field_name = self.delegate_field.lstrip("_")
            for item in class_def.body.body:
                if isinstance(item, cst.FunctionDef):
                    # Check if this is a getter method that delegates
                    if self._is_delegation_method(item, public_field_name):
                        self.delegation_methods.append(item.name.value)

    def _is_delegation_method(self, method: cst.FunctionDef, delegate_field: str) -> bool:
        """Check if a method is a delegation method.

        Args:
            method: The method to check
            delegate_field: The public field name (without underscore)

        Returns:
            True if the method is a delegation method
        """
        # Skip __init__ and magic methods
        if method.name.value.startswith("_"):
            return False

        # Check if method body is just returning self._field.something
        if not isinstance(method.body, cst.IndentedBlock):
            return False

        statements = method.body.body
        if len(statements) != 1:
            return False

        stmt = statements[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        if len(stmt.body) != 1:
            return False

        expr = stmt.body[0]
        if not isinstance(expr, cst.Return):
            return False

        if not expr.value:
            return False

        # Check if return value is self._field.something
        if isinstance(expr.value, cst.Attribute):
            obj = expr.value.value
            if isinstance(obj, cst.Attribute):
                if isinstance(obj.value, cst.Name) and obj.value.value == "self":
                    field_name = obj.attr.value
                    # Check if accessing delegate field
                    if field_name == self.delegate_field:
                        return True

        return False

    def _transform_field_assignment(
        self, stmt: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | None:
        """Transform field assignments to make private fields public.

        Args:
            stmt: The statement to transform

        Returns:
            The transformed statement or None if should be skipped
        """
        new_body = []
        for expr in stmt.body:
            if isinstance(expr, cst.Assign):
                # Transform self._field = value to self.field = value
                target = expr.targets[0].target
                if isinstance(target, cst.Attribute):
                    if isinstance(target.value, cst.Name) and target.value.value == "self":
                        field_name = target.attr.value
                        if field_name == self.delegate_field:
                            # Remove the leading underscore
                            public_name = field_name.lstrip("_")
                            new_target = target.with_changes(attr=cst.Name(public_name))
                            new_assign = expr.with_changes(
                                targets=[cst.AssignTarget(target=new_target)]
                            )
                            new_body.append(new_assign)
                            continue

            new_body.append(expr)

        if not new_body:
            return None

        return stmt.with_changes(body=new_body)


# Register the command
register_command(RemoveMiddleManCommand)
