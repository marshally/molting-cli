"""Move Method refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_self_field_assignment, parse_target
from molting.core.visitors import SelfFieldCollector


class MoveMethodCommand(BaseCommand):
    """Command to move a method from one class to another."""

    name = "move-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("source", "to")

    def execute(self) -> None:
        """Apply move-method refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        source = self.params["source"]
        to_class = self.params["to"]

        source_class, method_name = parse_target(source, expected_parts=2)
        self.apply_libcst_transform(MoveMethodTransformer, source_class, method_name, to_class)


class MoveMethodTransformer(cst.CSTTransformer):
    """Transforms code by moving a method from one class to another."""

    def __init__(self, source_class: str, method_name: str, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the class containing the method to move
            method_name: Name of the method to move
            target_class: Name of the class to move the method to
        """
        self.source_class = source_class
        self.method_name = method_name
        self.target_class = target_class
        self.method_to_move: cst.FunctionDef | None = None
        self.target_class_field: str | None = None

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class definitions to move the method."""
        if original_node.name.value == self.source_class:
            return self._process_source_class(updated_node)

        if original_node.name.value == self.target_class:
            return self._process_target_class(updated_node)

        return updated_node

    def _process_source_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Process the source class to find and replace the method.

        Args:
            node: The source class definition

        Returns:
            Updated class definition with the method replaced by a delegation call
        """
        updated_class_members: list[Any] = []
        method_found = False

        for item in node.body.body:
            if isinstance(item, cst.FunctionDef) and item.name.value == self.method_name:
                method_found = True
                self.method_to_move = item
                self.target_class_field = self._find_target_class_field(node)
                delegation_method = self._create_delegation_method(item)
                updated_class_members.append(delegation_method)
            else:
                updated_class_members.append(item)

        if not method_found:
            raise ValueError(
                f"Method '{self.method_name}' not found in class '{self.source_class}'"
            )

        return node.with_changes(body=node.body.with_changes(body=tuple(updated_class_members)))

    def _process_target_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Process the target class to add the moved method.

        Args:
            node: The target class definition

        Returns:
            Updated class definition with the new method added
        """
        if self.method_to_move is None:
            return node

        transformed_method = self._transform_method_for_target()
        method_with_spacing = transformed_method.with_changes(
            leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
        )

        updated_members = tuple(list(node.body.body) + [method_with_spacing])
        return node.with_changes(body=node.body.with_changes(body=updated_members))

    def _find_target_class_field(self, node: cst.ClassDef) -> str | None:
        """Find the field that references the target class.

        Args:
            node: The source class definition

        Returns:
            The field name that holds the target class instance, or None if not found
        """
        for item in node.body.body:
            if isinstance(item, cst.FunctionDef) and item.name.value == "__init__":
                return self._extract_field_from_init(item)
        return None

    def _extract_field_from_init(self, init_method: cst.FunctionDef) -> str | None:
        """Extract the field name from __init__ that holds the target class.

        Args:
            init_method: The __init__ method definition

        Returns:
            The field name, or None if not found
        """
        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                result = find_self_field_assignment(stmt)
                if result:
                    field_name, value = result
                    # Only return fields that are assigned from a parameter (Name node)
                    if isinstance(value, cst.Name):
                        return field_name
        return None

    def _create_delegation_method(self, original_method: cst.FunctionDef) -> cst.FunctionDef:
        """Create a delegation method that calls the moved method.

        Args:
            original_method: The original method being moved

        Returns:
            A new method that delegates to the target class
        """
        params_to_pass = self._collect_self_references(original_method)
        args = [
            cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name(param)))
            for param in params_to_pass
        ]

        if self.target_class_field is None:
            raise ValueError(
                f"Could not find field referencing target class '{self.target_class}' "
                f"in source class '{self.source_class}'"
            )

        delegation_call = cst.Return(
            value=cst.Call(
                func=cst.Attribute(
                    value=cst.Attribute(
                        value=cst.Name("self"),
                        attr=cst.Name(self.target_class_field),
                    ),
                    attr=cst.Name(self.method_name),
                ),
                args=args,
            )
        )

        delegation_body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[delegation_call])])
        return original_method.with_changes(body=delegation_body)

    def _collect_self_references(self, method: cst.FunctionDef) -> list[str]:
        """Collect self.field references that need to be passed as parameters.

        Args:
            method: The method to analyze

        Returns:
            List of field names that are referenced
        """
        exclude_fields = {self.target_class_field} if self.target_class_field else set()
        collector = SelfFieldCollector(exclude_fields=exclude_fields)
        method.visit(collector)
        return collector.collected_fields

    def _transform_method_for_target(self) -> cst.FunctionDef:
        """Transform the method to work in the target class.

        Returns:
            The transformed method with parameters instead of self references
        """
        if self.method_to_move is None:
            raise ValueError("No method to move")

        params_needed = self._collect_self_references(self.method_to_move)

        new_params = [cst.Param(name=cst.Name("self"))]
        for param_name in params_needed:
            new_params.append(cst.Param(name=cst.Name(param_name)))

        body_transformer = SelfReferenceReplacer(params_needed, self.target_class_field)
        transformed_body = self.method_to_move.body.visit(body_transformer)

        return self.method_to_move.with_changes(
            params=cst.Parameters(params=new_params), body=transformed_body
        )


class SelfReferenceReplacer(cst.CSTTransformer):
    """Replaces self.field with parameter references and self.target_field.x with self.x."""

    def __init__(self, fields_to_replace: list[str], target_class_field: str | None = None) -> None:
        """Initialize the replacer.

        Args:
            fields_to_replace: List of field names to replace with parameters
            target_class_field: The field that holds the target class (to be replaced with self)
        """
        self.fields_to_replace = fields_to_replace
        self.target_class_field = target_class_field

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute | cst.Name:
        """Replace self.field with parameter name or self.target_field.x with self.x."""
        if (
            isinstance(updated_node.value, cst.Attribute)
            and isinstance(updated_node.value.value, cst.Name)
            and updated_node.value.value.value == "self"
            and updated_node.value.attr.value == self.target_class_field
        ):
            return cst.Attribute(value=cst.Name("self"), attr=updated_node.attr)

        if isinstance(updated_node.value, cst.Name) and updated_node.value.value == "self":
            field_name = updated_node.attr.value
            if field_name in self.fields_to_replace:
                return cst.Name(field_name)
        return updated_node


# Register the command
register_command(MoveMethodCommand)
