"""Encapsulate Field refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter

INIT_METHOD_NAME = "__init__"


class EncapsulateFieldCommand(BaseCommand):
    """Encapsulate a public field by making it private with getter/setter methods.

    This refactoring converts a public class field into a private field and provides
    public accessor methods (@property getter and @setter) to control access to it.
    This is a fundamental refactoring that improves encapsulation and allows you to
    add validation, side effects, or other logic when the field is accessed or modified.

    **When to use:**
    - You have a public field that should be controlled by the class
    - You want to add validation or side effects to field access
    - You're preparing to modify field storage without affecting the public interface
    - You're improving encapsulation as part of a broader refactoring effort

    **Example:**
    Before:
        class Person:
            def __init__(self, name):
                self.name = name

        person = Person("Alice")
        person.name = "Bob"  # Direct access, no validation possible

    After:
        class Person:
            def __init__(self, name):
                self._name = name

            @property
            def name(self):
                return self._name

            @name.setter
            def name(self, value):
                self._name = value  # Can add validation here

        person = Person("Alice")
        person.name = "Bob"  # Access via property, validation possible
    """

    name = "encapsulate-field"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for encapsulate-field: 'target'")

    def execute(self) -> None:
        """Apply encapsulate-field refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = EncapsulateFieldTransformer(class_name, field_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class EncapsulateFieldTransformer(cst.CSTTransformer):
    """Transforms a public field into a private field with getter and setter."""

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the field
            field_name: Name of the field to encapsulate
        """
        self.class_name = class_name
        self.field_name = field_name
        self.private_field_name = f"_{field_name}"

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Modify the target class to encapsulate the field."""
        if updated_node.name.value != self.class_name:
            return updated_node

        new_body: list[cst.BaseStatement] = []

        # First pass: transform the __init__ method and other methods
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD_NAME:
                    new_body.append(self._transform_init_method(stmt))
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # Add property getter
        new_body.append(self._create_property_getter())

        # Add property setter
        new_body.append(self._create_property_setter())

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _is_field_assignment(self, target: cst.AssignTarget) -> bool:
        """Check if an assignment target is assigning to the target field.

        Args:
            target: The assignment target to check

        Returns:
            True if this is an assignment to self.field_name
        """
        if not isinstance(target.target, cst.Attribute):
            return False
        if not isinstance(target.target.value, cst.Name):
            return False
        return target.target.value.value == "self" and target.target.attr.value == self.field_name

    def _create_private_field_assignment(self, value: cst.BaseExpression) -> cst.Assign:
        """Create an assignment to the private field.

        Args:
            value: The value to assign

        Returns:
            Assignment statement for self._field_name = value
        """
        return cst.Assign(
            targets=[
                cst.AssignTarget(
                    target=cst.Attribute(
                        value=cst.Name("self"),
                        attr=cst.Name(self.private_field_name),
                    )
                )
            ],
            value=value,
        )

    def _transform_init_method(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform __init__ to use private field name.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                new_stmt_body: list[cst.BaseSmallStatement] = []
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        modified = False
                        for target in body_item.targets:
                            if self._is_field_assignment(target):
                                # Change self.name to self._name
                                new_assign = self._create_private_field_assignment(body_item.value)
                                new_stmt_body.append(new_assign)
                                modified = True
                                break
                        if not modified:
                            new_stmt_body.append(body_item)
                    else:
                        new_stmt_body.append(body_item)
                new_body.append(stmt.with_changes(body=new_stmt_body))
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_property_getter(self) -> cst.FunctionDef:
        """Create the @property getter method.

        Returns:
            Property getter method
        """
        return cst.FunctionDef(
            name=cst.Name(self.field_name),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Attribute(
                                    value=cst.Name("self"), attr=cst.Name(self.private_field_name)
                                )
                            )
                        ]
                    )
                ]
            ),
            decorators=[cst.Decorator(decorator=cst.Name("property"))],
            leading_lines=[cst.EmptyLine()],
        )

    def _create_property_setter(self) -> cst.FunctionDef:
        """Create the @name.setter method.

        Returns:
            Property setter method
        """
        return cst.FunctionDef(
            name=cst.Name(self.field_name),
            params=cst.Parameters(params=[create_parameter("self"), create_parameter("value")]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(
                                        target=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(self.private_field_name),
                                        )
                                    )
                                ],
                                value=cst.Name("value"),
                            )
                        ]
                    )
                ]
            ),
            decorators=[
                cst.Decorator(
                    decorator=cst.Attribute(
                        value=cst.Name(self.field_name), attr=cst.Name("setter")
                    )
                )
            ],
            leading_lines=[cst.EmptyLine()],
        )


# Register the command
register_command(EncapsulateFieldCommand)
