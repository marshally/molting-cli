"""Inline Class refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    extract_init_field_assignments,
    find_class_in_module,
    find_self_field_assignment,
)

INIT_METHOD_NAME = "__init__"


class InlineClassCommand(BaseCommand):
    """Command to inline a class into another class."""

    name = "inline-class"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("source_class", "into")

    def execute(self) -> None:
        """Apply inline-class refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        source_class = self.params["source_class"]
        target_class = self.params["into"]

        self.apply_libcst_transform(InlineClassTransformer, source_class, target_class)


class InlineClassTransformer(cst.CSTTransformer):
    """Transforms classes to inline source class into target class."""

    def __init__(self, source_class: str, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the class to be inlined
            target_class: Name of the class to inline into
        """
        self.source_class = source_class
        self.target_class = target_class
        self.source_class_def: cst.ClassDef | None = None
        self.source_fields: dict[str, cst.BaseExpression] = {}
        self.source_methods: list[cst.FunctionDef] = []
        self.field_prefix = ""

    def visit_Module(self, node: cst.Module) -> bool:  # noqa: N802
        """Visit module to find and analyze source class."""
        self.source_class_def = find_class_in_module(node, self.source_class)
        if self.source_class_def:
            self._extract_source_features(self.source_class_def)

        target_class_def = find_class_in_module(node, self.target_class)
        if target_class_def:
            self._determine_field_prefix(target_class_def)

        return True

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and remove the source class."""
        if not self.source_class_def:
            return updated_node

        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.source_class:
                    continue  # Skip the source class
            new_body.append(stmt)

        return updated_node.with_changes(body=tuple(new_body))

    def _get_source_method_names(self) -> set[str]:
        """Get names of methods from source class (excluding __init__).

        Returns:
            Set of method names from the source class
        """
        return {m.name.value for m in self.source_methods if m.name.value != INIT_METHOD_NAME}

    def _build_target_class_body(
        self, class_body: tuple[cst.BaseStatement, ...], source_method_names: set[str]
    ) -> list[cst.BaseStatement]:
        """Build the new body for the target class.

        Args:
            class_body: The original class body statements
            source_method_names: Names of methods being inlined

        Returns:
            List of statements for the new class body
        """
        new_body_stmts: list[cst.BaseStatement] = []
        for stmt in class_body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == INIT_METHOD_NAME:
                stmt = self._transform_init_method(stmt)
                new_body_stmts.append(stmt)
            elif isinstance(stmt, cst.FunctionDef) and stmt.name.value in source_method_names:
                continue
            else:
                new_body_stmts.append(stmt)
        return new_body_stmts

    def _add_inlined_methods(self, body_stmts: list[cst.BaseStatement]) -> None:
        """Add transformed methods from source class to target class body.

        Args:
            body_stmts: List of body statements to append to
        """
        for method in self.source_methods:
            if method.name.value != INIT_METHOD_NAME:
                transformed_method = self._transform_method(method)
                body_stmts.append(transformed_method)

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and inline source class if this is the target."""
        if original_node.name.value != self.target_class:
            return updated_node

        source_method_names = self._get_source_method_names()
        new_body_stmts = self._build_target_class_body(
            cast(tuple[cst.BaseStatement, ...], updated_node.body.body), source_method_names
        )
        self._add_inlined_methods(new_body_stmts)

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _is_source_class_instantiation(self, value: cst.BaseExpression) -> bool:
        """Check if a value is an instantiation of the source class.

        Args:
            value: The expression to check

        Returns:
            True if the value is a Call to the source class constructor
        """
        if isinstance(value, cst.Call):
            if isinstance(value.func, cst.Name):
                return value.func.value == self.source_class
        return False

    def _extract_source_features(self, class_def: cst.ClassDef) -> None:
        """Extract fields and methods from source class.

        Args:
            class_def: The source class definition
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                self.source_methods.append(stmt)
                if stmt.name.value == INIT_METHOD_NAME:
                    self.source_fields = extract_init_field_assignments(stmt)

    def _compute_prefix_from_field(self, field_name: str) -> str:
        """Compute the prefix from a delegation field name.

        Args:
            field_name: The delegation field name (e.g., "office_telephone")

        Returns:
            The prefix to use (e.g., "office_")
        """
        if "_" in field_name:
            parts = field_name.rsplit("_", 1)
            return parts[0] + "_"
        return ""

    def _determine_field_prefix(self, target_class_def: cst.ClassDef) -> None:
        """Determine the prefix to use for inlined fields.

        Args:
            target_class_def: The target class definition
        """
        for stmt in target_class_def.body.body:
            if not isinstance(stmt, cst.FunctionDef):
                continue
            if stmt.name.value != INIT_METHOD_NAME:
                continue
            if not isinstance(stmt.body, cst.IndentedBlock):
                continue

            for body_stmt in stmt.body.body:
                if isinstance(body_stmt, cst.SimpleStatementLine):
                    result = find_self_field_assignment(body_stmt)
                    if result:
                        field_name, value = result
                        if self._is_source_class_instantiation(value):
                            self.field_prefix = self._compute_prefix_from_field(field_name)
                            return

    def _transform_init_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform the __init__ method to inline source class fields.

        Args:
            node: The __init__ method to transform

        Returns:
            The transformed __init__ method
        """
        new_stmts: list[cst.BaseStatement] = []

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    result = find_self_field_assignment(stmt)
                    if result:
                        field_name, value = result
                        if self._is_source_class_instantiation(value):
                            for field_name, field_value in self.source_fields.items():
                                new_field_name = self.field_prefix + field_name
                                new_assignment = cst.SimpleStatementLine(
                                    body=[
                                        cst.Assign(
                                            targets=[
                                                cst.AssignTarget(
                                                    cst.Attribute(
                                                        value=cst.Name("self"),
                                                        attr=cst.Name(new_field_name),
                                                    )
                                                )
                                            ],
                                            value=field_value,
                                        )
                                    ]
                                )
                                new_stmts.append(new_assignment)
                        else:
                            new_stmts.append(stmt)
                    else:
                        new_stmts.append(stmt)
                else:
                    new_stmts.append(stmt)

        return node.with_changes(body=cst.IndentedBlock(body=new_stmts))

    def _transform_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a method from source class to use inlined fields.

        Args:
            method: The method to transform

        Returns:
            The transformed method
        """
        transformer = FieldReferenceTransformer(self.source_fields, self.field_prefix)
        return cast(cst.FunctionDef, method.visit(transformer))


class FieldReferenceTransformer(cst.CSTTransformer):
    """Transforms field references in methods."""

    def __init__(self, source_fields: dict[str, cst.BaseExpression], field_prefix: str) -> None:
        """Initialize the transformer.

        Args:
            source_fields: Dictionary of source class fields
            field_prefix: Prefix to add to field names
        """
        self.source_fields = source_fields
        self.field_prefix = field_prefix

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Leave attribute and update field references."""
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "self":
                field_name = updated_node.attr.value
                if field_name in self.source_fields:
                    new_field_name = self.field_prefix + field_name
                    return updated_node.with_changes(attr=cst.Name(new_field_name))

        return updated_node


register_command(InlineClassCommand)
