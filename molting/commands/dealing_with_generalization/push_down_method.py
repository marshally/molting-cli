"""Push Down Method refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    find_method_in_class,
    is_pass_statement,
    parse_target,
)


class PushDownMethodCommand(BaseCommand):
    """Command to push down a method from superclass to subclass."""

    name = "push-down-method"

    def validate(self) -> None:
        """Validate that required parameters are present and well-formed.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.validate_required_params("target", "to")

        # Validate target format (ClassName::method_name)
        try:
            parse_target(self.params["target"], expected_parts=2)
        except ValueError as e:
            raise ValueError(f"Invalid target format for push-down-method: {e}") from e

    def execute(self) -> None:
        """Apply push-down-method refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        to_class = self.params["to"]

        # Parse target to get class and method names
        class_name, method_name = parse_target(target, expected_parts=2)

        # Apply transformation
        self.apply_libcst_transform(PushDownMethodTransformer, class_name, method_name, to_class)


class PushDownMethodTransformer(cst.CSTTransformer):
    """Transforms a module by pushing down a method from superclass to subclass."""

    def __init__(self, source_class: str, method_name: str, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the superclass containing the method
            method_name: Name of the method to push down
            target_class: Name of the subclass to push the method to
        """
        self.source_class = source_class
        self.method_name = method_name
        self.target_class = target_class
        self.method_to_move: cst.FunctionDef | None = None

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to push down the method."""
        if original_node.name.value == self.source_class:
            # Remove method from source class
            return self._remove_method_from_class(updated_node)
        elif original_node.name.value == self.target_class:
            # Add method to target class
            return self._add_method_to_class(updated_node)
        return updated_node

    def _remove_method_from_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Remove method from source class.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body_stmts: list[cst.BaseStatement] = []

        # Find and capture the method to move
        method_to_remove = find_method_in_class(class_node, self.method_name)
        if method_to_remove:
            self.method_to_move = method_to_remove

        # Add all statements except the method to remove
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.method_name:
                continue  # Skip the method we're removing
            new_body_stmts.append(stmt)

        # If no statements remain, add pass
        if not new_body_stmts:
            new_body_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _add_method_to_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add method to target class.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        if not self.method_to_move:
            return class_node

        new_body_stmts: list[cst.BaseStatement] = []

        # Remove pass statements if present
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if not is_pass_statement(stmt):
                new_body_stmts.append(stmt)

        # Add the method to the class
        new_body_stmts.append(self.method_to_move)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )


# Register the command
register_command(PushDownMethodCommand)
