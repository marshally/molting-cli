"""Pull Up Method refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    find_method_in_class,
    is_pass_statement,
    parse_target,
)


class PullUpMethodCommand(BaseCommand):
    """Move identical methods from subclasses to their common superclass.

    The Pull Up Method refactoring consolidates duplicate methods that exist in
    multiple subclasses by moving them to the shared superclass. This eliminates
    code duplication and improves maintainability by ensuring the method logic
    is defined in a single location.

    **When to use:**
    - You have the same method implemented identically in multiple subclasses
    - The method uses only features available in the superclass
    - You want to reduce code duplication and improve consistency
    - Subclasses should inherit the method rather than redefine it

    **Example:**
    Before:
        class Animal:
            pass

        class Dog(Animal):
            def make_sound(self):
                return "Woof"

        class Cat(Animal):
            def make_sound(self):
                return "Woof"

    After:
        class Animal:
            def make_sound(self):
                return "Woof"

        class Dog(Animal):
            pass

        class Cat(Animal):
            pass
    """

    name = "pull-up-method"

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
            raise ValueError(f"Invalid target format for pull-up-method: {e}") from e

    def execute(self) -> None:
        """Apply pull-up-method refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        to_class = self.params["to"]

        # Parse target to get class and method names
        class_name, method_name = parse_target(target, expected_parts=2)

        # First pass: capture the method and check for conflicts
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        capture_transformer = MethodCaptureTransformer(class_name, method_name, to_class)
        module.visit(capture_transformer)

        # Check for name conflicts
        if capture_transformer.method_exists_in_target:
            # Method already exists in target, skip the refactoring
            return

        # Second pass: apply transformation with captured method
        move_transformer = PullUpMethodTransformer(
            class_name, method_name, to_class, capture_transformer.method_to_pull_up
        )
        modified_tree = module.visit(move_transformer)
        self.file_path.write_text(modified_tree.code)


class MethodCaptureTransformer(cst.CSTTransformer):
    """Visitor to capture method information from source and target classes."""

    def __init__(self, source_class: str, method_name: str, target_class: str) -> None:
        """Initialize the capture transformer.

        Args:
            source_class: Name of the class containing the method
            method_name: Name of the method to capture
            target_class: Name of the target class
        """
        self.source_class = source_class
        self.method_name = method_name
        self.target_class = target_class
        self.method_to_pull_up: cst.FunctionDef | None = None
        self.method_exists_in_target = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Capture method information when visiting classes."""
        if node.name.value == self.source_class:
            method = find_method_in_class(node, self.method_name)
            if method:
                self.method_to_pull_up = method
        elif node.name.value == self.target_class:
            # Check if method already exists in target
            method = find_method_in_class(node, self.method_name)
            if method:
                self.method_exists_in_target = True


class PullUpMethodTransformer(cst.CSTTransformer):
    """Transforms a module by pulling up a method from subclass to superclass."""

    def __init__(
        self,
        source_class: str,
        method_name: str,
        target_class: str,
        method_to_pull_up: cst.FunctionDef | None,
    ) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the subclass containing the method
            method_name: Name of the method to pull up
            target_class: Name of the superclass to pull the method to
            method_to_pull_up: The method to pull up (captured in first pass)
        """
        self.source_class = source_class
        self.method_name = method_name
        self.target_class = target_class
        self.method_to_pull_up = method_to_pull_up

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to pull up the method."""
        if original_node.name.value == self.source_class:
            # Remove method from source class
            return self._remove_method_from_class(updated_node)
        elif original_node.name.value == self.target_class:
            # Add method to target class
            return self._add_method_to_class(updated_node)
        else:
            # Check if this is a sibling class that also has the same method
            # and if so, remove it
            return self._remove_method_if_exists(updated_node)

    def _remove_method_from_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Remove the method from the class.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            # Skip the method we want to remove
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.method_name:
                continue
            new_body_stmts.append(stmt)

        # If no statements remain, add pass
        if not new_body_stmts:
            new_body_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _remove_method_if_exists(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Remove the method from this class if it exists.

        Args:
            class_node: The class definition to check

        Returns:
            Modified class definition
        """
        method = find_method_in_class(class_node, self.method_name)
        if method:
            return self._remove_method_from_class(class_node)
        return class_node

    def _add_method_to_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add the captured method to target class.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        if not self.method_to_pull_up:
            return class_node

        new_body_stmts: list[cst.BaseStatement] = []

        # Remove 'pass' statements if present
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if not is_pass_statement(stmt):
                new_body_stmts.append(stmt)

        # Add the method
        new_body_stmts.append(self.method_to_pull_up)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )


# Register the command
register_command(PullUpMethodCommand)
