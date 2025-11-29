"""Collapse Hierarchy refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import is_empty_class, parse_target


class CollapseHierarchyCommand(BaseCommand):
    """Collapse an empty subclass into its superclass by removing the subclass.

    This refactoring removes a subclass that has become redundant because it no
    longer differs from its superclass in any meaningful way. When a subclass
    only inherits from its superclass without adding new methods, fields, or
    overriding existing ones, it serves no purpose and should be removed to
    simplify the class hierarchy.

    This implementation specifically targets empty subclasses (those with no body
    or only containing a `pass` statement). All references to the subclass are
    expected to be updated to use the superclass directly.

    **When to use:**
    - After refactoring, a subclass no longer adds any value over its superclass
    - You want to simplify class hierarchies and reduce unnecessary abstractions
    - A subclass was created as a placeholder but never gained its own behavior
    - You're consolidating similar classes that share the same implementation

    **Example:**

    Before:
        class PaymentMethod:
            def pay(self, amount: float) -> None:
                pass

        class CreditCardPayment(PaymentMethod):
            pass  # No additional behavior

    After:
        class PaymentMethod:
            def pay(self, amount: float) -> None:
                pass

        # CreditCardPayment class is removed, code uses PaymentMethod directly
    """

    name = "collapse-hierarchy"

    def validate(self) -> None:
        """Validate that required parameters are present and well-formed.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.validate_required_params("target", "into")

        # Validate target class name format
        try:
            parse_target(self.params["target"], expected_parts=1)
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

        # Apply transformation
        self.apply_libcst_transform(CollapseHierarchyTransformer, class_name)


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
            if is_empty_class(original_node):
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


# Register the command
register_command(CollapseHierarchyCommand)
