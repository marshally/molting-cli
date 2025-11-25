"""Reusable CST visitor classes."""

import libcst as cst

from molting.core.ast_utils import is_self_attribute


class SelfFieldCollector(cst.CSTVisitor):
    """Collects all self.field references in a node.

    Example:
        collector = SelfFieldCollector(exclude_fields={"target_field"})
        method.visit(collector)
        fields = collector.collected_fields
    """

    def __init__(self, exclude_fields: set[str] | None = None) -> None:
        """Initialize the collector.

        Args:
            exclude_fields: Set of field names to exclude from collection
        """
        self.collected_fields: list[str] = []
        self.exclude_fields = exclude_fields or set()

    def visit_Attribute(self, node: cst.Attribute) -> None:  # noqa: N802
        """Visit attribute access to find self.field references."""
        if is_self_attribute(node):
            field_name = node.attr.value
            if field_name not in self.collected_fields and field_name not in self.exclude_fields:
                self.collected_fields.append(field_name)


class SelfFieldChecker(cst.CSTVisitor):
    """Checks if a node accesses any specified self fields.

    This is a boolean checking version of SelfFieldCollector that can short-circuit
    traversal after finding the first match, avoiding unnecessary traversal.

    Example:
        checker = SelfFieldChecker(target_fields={"employee", "age"})
        node.visit(checker)
        if checker.found:
            print("Node accesses one of the target fields")
    """

    def __init__(self, target_fields: set[str]) -> None:
        """Initialize the checker.

        Args:
            target_fields: Set of field names to check for
        """
        self.target_fields = target_fields
        self.found = False

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # noqa: N802
        """Visit attribute access to check for target self fields.

        Returns:
            False to stop traversal if a match is found, otherwise True.
        """
        if is_self_attribute(node):
            field_name = node.attr.value
            if field_name in self.target_fields:
                self.found = True
                return False  # Stop traversal
        return True
