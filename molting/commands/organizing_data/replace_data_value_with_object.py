"""Replace Data Value with Object refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class ReplaceDataValueWithObjectCommand(BaseCommand):
    """Command to replace a primitive value with an object."""

    name = "replace-data-value-with-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for replace-data-value-with-object: 'target'"
            )
        if "name" not in self.params:
            raise ValueError(
                "Missing required parameter for replace-data-value-with-object: 'name'"
            )

    def execute(self) -> None:
        """Apply replace-data-value-with-object refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        new_class_name = self.params["name"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ReplaceDataValueWithObjectTransformer(class_name, field_name, new_class_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceDataValueWithObjectTransformer(cst.CSTTransformer):
    """Transforms a primitive value field into an object."""

    def __init__(self, class_name: str, field_name: str, new_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the field
            field_name: Name of the field to replace
            new_class_name: Name of the new class to create
        """
        self.class_name = class_name
        self.field_name = field_name
        self.new_class_name = new_class_name

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the new class to the module."""
        # Find the target class and modify it
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.class_name:
                    # Modify the class that contains the field
                    modified_class = self._modify_class(stmt)
                    new_body.append(modified_class)
                else:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        # Insert the new class at the beginning
        new_class = self._create_new_class()
        new_body.insert(0, new_class)
        new_body.insert(1, cst.EmptyLine())

        return updated_node.with_changes(body=tuple(new_body))

    def _modify_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the original class to use the new object.

        Args:
            class_def: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == "__init__":
                    # Modify __init__ to instantiate the new class
                    modified_init = self._modify_init_method(stmt)
                    new_body.append(modified_init)
                else:
                    # Update method body to use new_class_name.field_name
                    modified_method = self._modify_method_body(stmt)
                    new_body.append(modified_method)
            else:
                new_body.append(stmt)

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_init_method(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify __init__ to instantiate the new class.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                modified_stmt = False
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        # Check if this is assignment to self.field_name
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Attribute):
                                if (
                                    isinstance(target.target.value, cst.Name)
                                    and target.target.value.value == "self"
                                    and target.target.attr.value == self.field_name
                                ):
                                    # Replace with self.field_name = NewClass(value)
                                    new_stmt = self._create_object_assignment(body_item.value)
                                    new_body_stmts.append(new_stmt)
                                    modified_stmt = True
                                    break
                if not modified_stmt:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body_stmts))

    def _create_object_assignment(
        self, original_value: cst.BaseExpression
    ) -> cst.SimpleStatementLine:
        """Create assignment statement that instantiates the new class.

        Args:
            original_value: The original value expression

        Returns:
            New assignment statement
        """
        new_call = cst.Call(
            func=cst.Name(self.new_class_name),
            args=[cst.Arg(value=original_value)],
        )

        return cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(self.field_name),
                            )
                        )
                    ],
                    value=new_call,
                )
            ]
        )

    def _modify_method_body(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Update method body to use the new object's attribute.

        Args:
            method: The method to modify

        Returns:
            Modified method
        """
        transformer = FieldAccessTransformer(self.field_name, self.new_class_name)
        new_method = method.visit(transformer)
        return cast(cst.FunctionDef, new_method)

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new class.

        Returns:
            New class definition
        """
        # Extract the parameter name from the original __init__
        # For now, we'll use 'name' as the parameter and field name
        param_name = "name"

        # Create __init__ method
        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(name=cst.Name(param_name)),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(
                                        target=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(param_name),
                                        )
                                    )
                                ],
                                value=cst.Name(param_name),
                            )
                        ]
                    )
                ]
            ),
        )

        return cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[],
            body=cst.IndentedBlock(body=[init_method]),
        )


class FieldAccessTransformer(cst.CSTTransformer):
    """Transforms field access to use the new object's attribute."""

    def __init__(self, field_name: str, new_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            field_name: The field name being replaced
            new_class_name: The new class name
        """
        self.field_name = field_name
        self.new_class_name = new_class_name

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Transform self.field_name to self.field_name.attribute.

        Args:
            original_node: The original attribute node
            updated_node: The updated attribute node

        Returns:
            Transformed attribute node
        """
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "self" and updated_node.attr.value == self.field_name:
                # Transform self.customer -> self.customer.name
                # We need to return an attribute that accesses the stored object's name
                return cst.Attribute(
                    value=updated_node,
                    attr=cst.Name("name"),
                )

        return updated_node


# Register the command
register_command(ReplaceDataValueWithObjectCommand)
