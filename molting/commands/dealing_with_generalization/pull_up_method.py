"""Pull Up Method refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_class, is_pass_statement, parse_target


class PullUpMethodCommand(BaseCommand):
    """Command to pull up a method from subclasses to superclass."""

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

        # Read file
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # First pass: collect method and identify subclasses
        collector = MethodCollector(class_name, method_name, to_class)
        module.visit(collector)

        # Validate that we found the method to pull up
        if collector.method_to_pull_up is None:
            raise ValueError(
                f"Method '{method_name}' not found in class '{class_name}'. "
                "Ensure the method exists and the target class is correct."
            )

        # Second pass: apply transformation
        transformer = PullUpMethodTransformer(
            method_name, to_class, collector.method_to_pull_up, collector.subclasses
        )
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class MethodCollector(cst.CSTVisitor):
    """Collects method information from the source class."""

    def __init__(self, source_class: str, method_name: str, target_class: str) -> None:
        """Initialize the collector.

        Args:
            source_class: Name of the subclass containing the method
            method_name: Name of the method to pull up
            target_class: Name of the superclass to pull the method to
        """
        self.source_class = source_class
        self.method_name = method_name
        self.target_class = target_class
        self.method_to_pull_up: cst.FunctionDef | None = None
        self.subclasses: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definitions to collect subclasses and the method."""
        class_name = node.name.value

        if self._is_subclass_of_target(node):
            self.subclasses.append(class_name)
            if class_name == self.source_class:
                self._capture_method_from_class(node)

        return True

    def _is_subclass_of_target(self, node: cst.ClassDef) -> bool:
        """Check if a class is a subclass of the target class.

        Args:
            node: The class definition to check

        Returns:
            True if the class inherits from the target class
        """
        if not node.bases:
            return False

        for base in node.bases:
            if isinstance(base.value, cst.Name) and base.value.value == self.target_class:
                return True

        return False

    def _capture_method_from_class(self, node: cst.ClassDef) -> None:
        """Capture the method definition from the class.

        Args:
            node: The class definition to extract the method from
        """
        method = find_method_in_class(node, self.method_name)
        if method:
            self.method_to_pull_up = method


class PullUpMethodTransformer(cst.CSTTransformer):
    """Transforms a module by pulling up a method from subclasses to superclass."""

    def __init__(
        self,
        method_name: str,
        target_class: str,
        method_to_pull_up: cst.FunctionDef | None,
        subclasses: list[str],
    ) -> None:
        """Initialize the transformer.

        Args:
            method_name: Name of the method to pull up
            target_class: Name of the superclass to pull the method to
            method_to_pull_up: The method definition to add to the superclass
            subclasses: List of subclass names to remove the method from
        """
        self.method_name = method_name
        self.target_class = target_class
        self.method_to_pull_up = method_to_pull_up
        self.subclasses = subclasses

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to pull up the method."""
        class_name = original_node.name.value

        if class_name == self.target_class:
            # Add method to target class
            return self._add_method_to_class(updated_node)
        elif class_name in self.subclasses:
            # Remove method from subclasses
            return self._remove_method_from_class(updated_node)
        return updated_node

    def _add_method_to_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add the method to the target class.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        if not self.method_to_pull_up:
            return class_node

        new_body_stmts: list[cst.BaseStatement] = []

        # Remove pass statements from empty class
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if not is_pass_statement(stmt):
                new_body_stmts.append(stmt)

        # Add the method
        new_body_stmts.append(self.method_to_pull_up)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _remove_method_from_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Remove the method from a subclass.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            # Skip the method we're pulling up
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.method_name:
                continue
            new_body_stmts.append(stmt)

        # If no statements remain, add pass
        if not new_body_stmts:
            new_body_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )


# Register the command
register_command(PullUpMethodCommand)
