"""Move Field refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import camel_to_snake_case, is_pass_statement, is_self_attribute
from molting.core.code_generation_utils import (
    create_field_assignment,
    create_init_method,
    create_parameter,
)


class MoveFieldCommand(BaseCommand):
    """Command to move a field from one class to another."""

    name = "move-field"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "source" not in self.params:
            raise ValueError("Missing required parameter for move-field: 'source'")
        if "to" not in self.params:
            raise ValueError("Missing required parameter for move-field: 'to'")

    def execute(self) -> None:
        """Apply move-field refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        source = self.params["source"]
        target_class = self.params["to"]

        parts = source.split("::")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid source format: {source}. Expected format: ClassName::field_name"
            )

        source_class = parts[0]
        field_name = parts[1]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = MoveFieldTransformer(source_class, field_name, target_class)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class MoveFieldTransformer(cst.CSTTransformer):
    """Transforms classes to move a field from one class to another."""

    def __init__(self, source_class: str, field_name: str, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the class to move the field from
            field_name: Name of the field to move
            target_class: Name of the class to move the field to
        """
        self.source_class = source_class
        self.field_name = field_name
        self.target_class = target_class
        # Convert camelCase/PascalCase to snake_case
        self.target_class_lower = camel_to_snake_case(target_class)
        self.field_value: cst.BaseExpression | None = None

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and update as needed."""
        if original_node.name.value == self.source_class:
            return self._transform_source_class(updated_node)
        elif original_node.name.value == self.target_class:
            return self._transform_target_class(updated_node)
        return updated_node

    def _transform_source_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the source class to remove field and add reference to target class."""
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                new_init = self._transform_source_init(stmt)
                new_body_stmts.append(new_init)
            elif isinstance(stmt, cst.FunctionDef):
                new_method = self._update_field_references(stmt)
                new_body_stmts.append(new_method)
            else:
                new_body_stmts.append(stmt)

        return node.with_changes(body=node.body.with_changes(body=tuple(new_body_stmts)))

    def _is_field_assignment(self, assign_node: cst.Assign) -> bool:
        """Check if an assignment is for the field we're moving.

        Args:
            assign_node: The assignment node to check

        Returns:
            True if this assigns to self.field_name
        """
        for target in assign_node.targets:
            if isinstance(target.target, cst.Attribute):
                if is_self_attribute(target.target, self.field_name):
                    return True
        return False

    def _transform_source_init(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform source class __init__ to remove field and add target class parameter."""
        new_params = list(node.params.params)
        new_stmts: list[cst.BaseStatement] = []

        new_params.append(create_parameter(self.target_class_lower))

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    keep_stmt = True
                    for item in stmt.body:
                        if isinstance(item, cst.Assign) and self._is_field_assignment(item):
                            self.field_value = item.value
                            keep_stmt = False
                            break
                    if keep_stmt:
                        new_stmts.append(stmt)
                else:
                    new_stmts.append(stmt)

            target_assignment = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                cst.Attribute(
                                    value=cst.Name("self"), attr=cst.Name(self.target_class_lower)
                                )
                            )
                        ],
                        value=cst.Name(self.target_class_lower),
                    )
                ]
            )
            new_stmts.append(target_assignment)

        return node.with_changes(
            params=cst.Parameters(params=new_params),
            body=cst.IndentedBlock(body=tuple(new_stmts)),
        )

    def _update_field_references(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Update references to the moved field in methods."""
        transformer = FieldReferenceUpdater(self.field_name, self.target_class_lower)
        return cast(cst.FunctionDef, node.visit(transformer))

    def _transform_target_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the target class to add the field."""
        has_init = False
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                has_init = True
                new_init = self._add_field_to_init(stmt)
                new_body_stmts.append(new_init)
            elif is_pass_statement(stmt):
                # Skip pass statements - they're placeholders for empty classes
                continue
            else:
                new_body_stmts.append(stmt)

        if not has_init:
            new_init = self._create_init_with_field()
            new_body_stmts.insert(0, new_init)

        return node.with_changes(body=node.body.with_changes(body=tuple(new_body_stmts)))

    def _add_field_to_init(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Add the field assignment to existing __init__."""
        new_stmts: list[cst.BaseStatement] = []

        if isinstance(node.body, cst.IndentedBlock):
            new_stmts = list(node.body.body)

        field_value = self.field_value if self.field_value else cst.Float("0.05")
        new_stmts.append(create_field_assignment(self.field_name, field_value))

        return node.with_changes(body=cst.IndentedBlock(body=tuple(new_stmts)))

    def _create_init_with_field(self) -> cst.FunctionDef:
        """Create a new __init__ method with the field."""
        field_value = self.field_value if self.field_value else cst.Float("0.05")
        return create_init_method(
            params=[],
            field_assignments={self.field_name: field_value},
        )


class FieldReferenceUpdater(cst.CSTTransformer):
    """Updates references to a field to use a different path."""

    def __init__(self, field_name: str, target_class_lower: str) -> None:
        """Initialize the updater.

        Args:
            field_name: Name of the field to update
            target_class_lower: Name of the target class reference
        """
        self.field_name = field_name
        self.target_class_lower = target_class_lower

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute | cst.BaseExpression:
        """Update attribute access to moved field."""
        if is_self_attribute(updated_node, self.field_name):
            return cst.Attribute(
                value=cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.target_class_lower)),
                attr=cst.Name(self.field_name),
            )
        return updated_node


register_command(MoveFieldCommand)
