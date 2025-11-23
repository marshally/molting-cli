"""Reusable CST visitor classes."""

import libcst as cst


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
        if isinstance(node.value, cst.Name) and node.value.value == "self":
            field_name = node.attr.value
            if field_name not in self.collected_fields and field_name not in self.exclude_fields:
                self.collected_fields.append(field_name)
