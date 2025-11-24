"""Push Down Field refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    find_method_in_class,
    is_pass_statement,
    parse_target,
    statements_contain_only_pass,
)


class PushDownFieldCommand(BaseCommand):
    """Command to push down a field from superclass to subclass."""

    name = "push-down-field"

    def validate(self) -> None:
        """Validate that required parameters are present and well-formed.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.validate_required_params("target", "to")

        # Validate target format (ClassName::field_name)
        try:
            parse_target(self.params["target"], expected_parts=2)
        except ValueError as e:
            raise ValueError(f"Invalid target format for push-down-field: {e}") from e

    def execute(self) -> None:
        """Apply push-down-field refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        to_class = self.params["to"]

        # Parse target to get class and field names
        class_name, field_name = parse_target(target, expected_parts=2)

        # Apply transformation
        self.apply_libcst_transform(PushDownFieldTransformer, class_name, field_name, to_class)


class PushDownFieldTransformer(cst.CSTTransformer):
    """Transforms a module by pushing down a field from superclass to subclass."""

    def __init__(self, source_class: str, field_name: str, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the superclass containing the field
            field_name: Name of the field to push down
            target_class: Name of the subclass to push the field to
        """
        self.source_class = source_class
        self.field_name = field_name
        self.target_class = target_class
        self.field_value: cst.BaseExpression | None = None

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to push down the field."""
        if original_node.name.value == self.source_class:
            # Remove field from source class __init__
            return self._remove_field_from_class(updated_node)
        elif original_node.name.value == self.target_class:
            # Add field to target class __init__
            return self._add_field_to_class(updated_node)
        return updated_node

    def _remove_field_from_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Remove field assignment from source class __init__.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body_stmts: list[cst.BaseStatement] = []

        # Find and process __init__ method
        init_method = find_method_in_class(class_node, "__init__")
        if init_method:
            modified_init = self._remove_field_from_init(init_method)
            if modified_init:
                new_body_stmts.append(modified_init)

        # Add all other statements
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                continue  # Skip __init__, already processed above
            new_body_stmts.append(stmt)

        # If no statements remain, add pass
        if not new_body_stmts:
            new_body_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _remove_field_from_init(self, init_node: cst.FunctionDef) -> cst.FunctionDef | None:
        """Remove field assignment from __init__ method.

        Args:
            init_node: The __init__ method to modify

        Returns:
            Modified __init__ method, or None if it becomes empty
        """
        if not isinstance(init_node.body, cst.IndentedBlock):
            return init_node

        new_stmts: list[cst.BaseStatement] = []

        for stmt in init_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this is the field assignment
                if not self._is_field_assignment(stmt):
                    new_stmts.append(stmt)
                else:
                    # Capture field value for later use
                    self._capture_field_value(stmt)
            else:
                new_stmts.append(stmt)

        # If __init__ becomes empty or only has pass, return None to remove it
        if not new_stmts or statements_contain_only_pass(new_stmts):
            return None

        return init_node.with_changes(body=cst.IndentedBlock(body=new_stmts))

    def _is_field_assignment(self, stmt: cst.SimpleStatementLine) -> bool:
        """Check if statement assigns to the field.

        Args:
            stmt: Statement to check

        Returns:
            True if statement assigns to the field
        """
        for body_stmt in stmt.body:
            if not isinstance(body_stmt, cst.Assign):
                continue

            for target in body_stmt.targets:
                if self._is_self_field_attribute(target.target):
                    return True
        return False

    def _is_self_field_attribute(self, node: cst.BaseExpression) -> bool:
        """Check if node is self.field_name attribute.

        Args:
            node: Expression to check

        Returns:
            True if node is self.field_name
        """
        if not isinstance(node, cst.Attribute):
            return False
        if not isinstance(node.value, cst.Name):
            return False
        return node.value.value == "self" and node.attr.value == self.field_name

    def _capture_field_value(self, stmt: cst.SimpleStatementLine) -> None:
        """Capture the value assigned to the field.

        Args:
            stmt: Statement containing field assignment
        """
        for body_stmt in stmt.body:
            if isinstance(body_stmt, cst.Assign):
                self.field_value = body_stmt.value

    def _add_field_to_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add field to target class __init__.

        Args:
            class_node: The class definition to modify

        Returns:
            Modified class definition
        """
        # First, check if class already has __init__
        init_method = find_method_in_class(class_node, "__init__")
        has_init = init_method is not None

        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if stmt is init_method:
                # Add field assignment to existing __init__
                modified_init = self._add_field_to_init(init_method)
                new_body_stmts.append(modified_init)
            else:
                # Skip 'pass' statements if we're adding a new __init__
                if not has_init and is_pass_statement(stmt):
                    continue
                new_body_stmts.append(stmt)

        if not has_init:
            # Create new __init__ with super().__init__() and field assignment
            new_init = self._create_init_with_field()
            new_body_stmts.insert(0, new_init)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _create_field_assignment_statement(self) -> cst.SimpleStatementLine:
        """Create a field assignment statement.

        Returns:
            Field assignment statement
        """
        field_value = self.field_value if self.field_value else cst.Integer("0")
        return cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.field_name))
                        )
                    ],
                    value=field_value,
                )
            ]
        )

    def _create_init_with_field(self) -> cst.FunctionDef:
        """Create new __init__ method with super call and field assignment.

        Returns:
            New __init__ method
        """
        # Create super().__init__() call
        super_call = cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Call(func=cst.Name("super"), args=[]),
                            attr=cst.Name("__init__"),
                        ),
                        args=[],
                    )
                )
            ]
        )

        field_assignment = self._create_field_assignment_statement()

        return cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(body=[super_call, field_assignment]),
        )

    def _add_field_to_init(self, init_node: cst.FunctionDef) -> cst.FunctionDef:
        """Add field assignment to existing __init__ method.

        Args:
            init_node: Existing __init__ method

        Returns:
            Modified __init__ method
        """
        if not isinstance(init_node.body, cst.IndentedBlock):
            return init_node

        field_assignment = self._create_field_assignment_statement()
        new_stmts = list(init_node.body.body) + [field_assignment]

        return init_node.with_changes(body=cst.IndentedBlock(body=new_stmts))


# Register the command
register_command(PushDownFieldCommand)
