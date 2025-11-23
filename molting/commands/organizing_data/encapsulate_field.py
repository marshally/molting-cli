"""Encapsulate Field refactoring command."""


import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class EncapsulateFieldCommand(BaseCommand):
    """Command to encapsulate a public field with getter and setter."""

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
                if stmt.name.value == "__init__":
                    new_body.append(self._transform_init_method(stmt))
                else:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        # Add property getter
        new_body.append(self._create_property_getter())

        # Add property setter
        new_body.append(self._create_property_setter())

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

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
                            if isinstance(target.target, cst.Attribute):
                                if (
                                    isinstance(target.target.value, cst.Name)
                                    and target.target.value.value == "self"
                                    and target.target.attr.value == self.field_name
                                ):
                                    # Change self.name to self._name
                                    new_assign = cst.Assign(
                                        targets=[
                                            cst.AssignTarget(
                                                target=cst.Attribute(
                                                    value=cst.Name("self"),
                                                    attr=cst.Name(self.private_field_name),
                                                )
                                            )
                                        ],
                                        value=body_item.value,
                                    )
                                    new_stmt_body.append(new_assign)
                                    modified = True
                                    break
                        if not modified:
                            new_stmt_body.append(body_item)
                    else:
                        new_stmt_body.append(body_item)
                new_body.append(stmt.with_changes(body=new_stmt_body))
            else:
                new_body.append(stmt)

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_property_getter(self) -> cst.FunctionDef:
        """Create the @property getter method.

        Returns:
            Property getter method
        """
        return cst.FunctionDef(
            name=cst.Name(self.field_name),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
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
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self")), cst.Param(name=cst.Name("value"))]
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
