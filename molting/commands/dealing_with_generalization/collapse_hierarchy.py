"""Collapse Hierarchy refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class CollapseHierarchyCommand(BaseCommand):
    """Command to collapse an empty subclass into its superclass."""

    name = "collapse-hierarchy"

    def validate(self) -> None:
        """Validate that required parameters are present and well-formed.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        try:
            target = self.params["target"]
            _ = self.params["into"]
        except KeyError as e:
            raise ValueError(f"Missing required parameter for collapse-hierarchy: {e}") from e

        # Validate target class name format
        try:
            parse_target(target, expected_parts=1)
        except ValueError as e:
            raise ValueError(f"Invalid target format for collapse-hierarchy: {e}") from e

    def execute(self) -> None:
        """Apply collapse-hierarchy refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target"]
        _ = self.params["into"]  # Validated but not needed for simple collapse

        # Parse target to get class name
        class_name = parse_target(target_class, expected_parts=1)[0]

        # Read file
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Apply transformation
        transformer = CollapseHierarchyTransformer(class_name)
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class CollapseHierarchyTransformer(cst.CSTTransformer):
    """Transforms a module by removing an empty subclass."""

    def __init__(self, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to remove
        """
        self.target_class = target_class

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.RemovalSentinel:
        """Remove empty subclass definitions."""
        if original_node.name.value == self.target_class:
            # Check if this class is empty (only contains pass or has no body)
            if self._is_empty_class(original_node):
                return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Clean up trailing empty lines after class removal."""
        new_body = list(updated_node.body)

        # Remove trailing empty lines for cleaner output
        while new_body and isinstance(new_body[-1], cst.EmptyLine):
            new_body.pop()

        return updated_node.with_changes(body=tuple(new_body))

    @staticmethod
    def _is_empty_class(node: cst.ClassDef) -> bool:
        """Check if a class is empty (contains only pass or no statements).

        Args:
            node: The class definition to check

        Returns:
            True if the class is empty
        """
        if isinstance(node.body, cst.IndentedBlock):
            # Check if body contains only pass or empty statements
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    # Check if this line only contains 'pass'
                    if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Pass):
                        continue
                else:
                    # Any other statement means it's not empty
                    return False
            return True
        return True


# Register the command
register_command(CollapseHierarchyCommand)
