"""Reusable CST transformer classes for common refactoring operations."""

from typing import Callable

import libcst as cst


class SelfFieldRenameTransformer(cst.CSTTransformer):
    """Generic transformer for renaming self.field references.

    This transformer supports three modes of operation:
    1. field_mapping: Dictionary mapping old field names to new field names
    2. field_prefix: Add a prefix to specified field names
    3. field_names with custom transform: Apply custom transformation to field names

    Examples:
        # Rename specific fields using a mapping
        transformer = SelfFieldRenameTransformer(
            field_mapping={"old_name": "new_name", "foo": "bar"}
        )

        # Add prefix to specific fields
        transformer = SelfFieldRenameTransformer(
            field_prefix="_",
            field_names={"private_field", "another_field"}
        )

        # Custom transformation function
        transformer = SelfFieldRenameTransformer(
            field_names={"field1", "field2"},
            transform_fn=lambda name: f"_{name}"
        )

        # Combine field_mapping with field_prefix (prefix applied first)
        transformer = SelfFieldRenameTransformer(
            field_mapping={"office_number": "number"},
            field_prefix="office_"
        )
    """

    def __init__(
        self,
        field_mapping: dict[str, str] | None = None,
        field_prefix: str | None = None,
        field_names: set[str] | None = None,
        transform_fn: Callable[[str], str] | None = None,
    ) -> None:
        """Initialize the transformer.

        Args:
            field_mapping: Dictionary mapping old field names to new field names
            field_prefix: Prefix to add to field names (used with field_names)
            field_names: Set of field names to transform (required if using field_prefix)
            transform_fn: Custom function to transform field names (used with field_names)

        Raises:
            ValueError: If configuration is invalid
        """
        if field_mapping is None and field_prefix is None and transform_fn is None:
            raise ValueError(
                "Must provide at least one of: field_mapping, field_prefix, or transform_fn"
            )

        if (field_prefix is not None or transform_fn is not None) and field_names is None:
            raise ValueError("field_names must be provided when using field_prefix or transform_fn")

        self.field_mapping = field_mapping or {}
        self.field_prefix = field_prefix
        self.field_names = field_names or set()
        self.transform_fn = transform_fn

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Transform self.field references according to configuration.

        Args:
            original_node: The original attribute node
            updated_node: The updated attribute node

        Returns:
            The transformed attribute node with renamed field
        """
        # Only transform self.field references
        if not isinstance(updated_node.value, cst.Name):
            return updated_node
        if updated_node.value.value != "self":
            return updated_node

        field_name = updated_node.attr.value

        # Apply field_mapping first
        if field_name in self.field_mapping:
            new_name = self.field_mapping[field_name]
            return updated_node.with_changes(attr=cst.Name(new_name))

        # Apply prefix or custom transform if field is in field_names
        if field_name in self.field_names:
            if self.transform_fn is not None:
                new_name = self.transform_fn(field_name)
                return updated_node.with_changes(attr=cst.Name(new_name))
            elif self.field_prefix is not None:
                new_name = f"{self.field_prefix}{field_name}"
                return updated_node.with_changes(attr=cst.Name(new_name))

        return updated_node


class FieldAccessCollector(cst.CSTVisitor):
    """Visitor that collects all self.field accesses.

    This is an alias for SelfFieldCollector in visitors.py, provided here
    for convenience and consistency with SelfFieldRenameTransformer.

    Examples:
        collector = FieldAccessCollector(exclude_fields={"skip_this"})
        method_node.visit(collector)
        all_fields = collector.collected_fields
    """

    def __init__(self, exclude_fields: set[str] | None = None) -> None:
        """Initialize the collector.

        Args:
            exclude_fields: Set of field names to exclude from collection
        """
        self.collected_fields: list[str] = []
        self.exclude_fields = exclude_fields or set()

    def visit_Attribute(self, node: cst.Attribute) -> None:  # noqa: N802
        """Visit attribute access to find self.field references.

        Args:
            node: The attribute node to visit
        """
        if isinstance(node.value, cst.Name) and node.value.value == "self":
            field_name = node.attr.value
            if field_name not in self.collected_fields and field_name not in self.exclude_fields:
                self.collected_fields.append(field_name)
