"""Self Encapsulate Field refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class SelfEncapsulateFieldCommand(BaseCommand):
    """Command to encapsulate direct field access with getter and setter properties."""

    name = "self-encapsulate-field"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for self-encapsulate-field: 'target'")

    def execute(self) -> None:
        """Apply self-encapsulate-field refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = SelfEncapsulateFieldTransformer(class_name, field_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class SelfEncapsulateFieldTransformer(cst.CSTTransformer):
    """Transforms direct field access to use properties."""

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
        """Transform the target class to use properties.

        Args:
            original_node: The original class definition
            updated_node: The updated class definition

        Returns:
            Transformed class definition with properties
        """
        if updated_node.name.value != self.class_name:
            return updated_node

        new_body, property_exists, last_property_index, init_index = self._process_class_body(
            updated_node.body.body
        )

        if property_exists:
            return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

        insert_index = last_property_index + 1 if last_property_index >= 0 else init_index + 1
        final_body = self._insert_properties_at_index(new_body, insert_index)
        return updated_node.with_changes(body=cst.IndentedBlock(body=final_body))

    def _process_class_body(self, body: Any) -> tuple[list[Any], bool, int, int]:
        """Process class body to transform init and track property locations.

        Args:
            body: Class body statements

        Returns:
            Tuple of (new_body, property_exists, last_property_index, init_index)
        """
        new_body: list[Any] = []
        property_exists = False
        last_property_index = -1
        init_index = -1

        for stmt in body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == "__init__":
                    new_body.append(self._transform_init_method(stmt))
                    init_index = len(new_body) - 1
                elif stmt.name.value == self.field_name:
                    property_exists = True
                    new_body.append(stmt)
                elif self._is_property_method(stmt):
                    new_body.append(stmt)
                    last_property_index = len(new_body) - 1
                else:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        return new_body, property_exists, last_property_index, init_index

    def _insert_properties_at_index(self, body: list[Any], insert_index: int) -> list[Any]:
        """Insert property getter and setter at specified index.

        Args:
            body: Class body statements
            insert_index: Index after which to insert properties

        Returns:
            New body with properties inserted
        """
        final_body: list[Any] = []
        for i, stmt in enumerate(body):
            final_body.append(stmt)
            if i == insert_index - 1:
                final_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                final_body.append(self._create_property_getter())
                final_body.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                final_body.append(self._create_property_setter())
        return final_body

    def _is_property_method(self, node: cst.FunctionDef) -> bool:
        """Check if a function is a property getter or setter.

        Args:
            node: Function definition to check

        Returns:
            True if function has @property or @<name>.setter decorator
        """
        for decorator in node.decorators:
            if isinstance(decorator.decorator, cst.Name):
                if decorator.decorator.value == "property":
                    return True
            elif isinstance(decorator.decorator, cst.Attribute):
                if decorator.decorator.attr.value == "setter":
                    return True
        return False

    def _transform_init_method(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform __init__ to use private field name.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body: list[Any] = []

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                modified_stmt = self._try_rename_field_assignment(stmt)
                new_body.append(modified_stmt if modified_stmt else stmt)
            else:
                new_body.append(stmt)

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _try_rename_field_assignment(
        self, stmt: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | None:
        """Try to rename field assignment to use private name.

        Args:
            stmt: Statement line to check

        Returns:
            Modified statement if it assigns to target field, None otherwise
        """
        for body_item in stmt.body:
            if isinstance(body_item, cst.Assign):
                for target in body_item.targets:
                    if self._is_assignment_to_field(target.target):
                        new_target = self._create_private_field_target()
                        new_assign = body_item.with_changes(targets=[new_target])
                        return stmt.with_changes(body=[new_assign])
        return None

    def _is_assignment_to_field(self, target: cst.BaseExpression) -> bool:
        """Check if target is assignment to self.field_name.

        Args:
            target: Assignment target to check

        Returns:
            True if target is self.field_name
        """
        if not isinstance(target, cst.Attribute):
            return False
        if not isinstance(target.value, cst.Name):
            return False
        return target.value.value == "self" and target.attr.value == self.field_name

    def _create_private_field_target(self) -> cst.AssignTarget:
        """Create assignment target for private field.

        Returns:
            Assignment target for self._field_name
        """
        return cst.AssignTarget(
            target=cst.Attribute(
                value=cst.Name("self"),
                attr=cst.Name(self.private_field_name),
            )
        )

    def _create_property_getter(self) -> cst.FunctionDef:
        """Create property getter method.

        Returns:
            Property getter function definition
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
                                    value=cst.Name("self"),
                                    attr=cst.Name(self.private_field_name),
                                )
                            )
                        ]
                    )
                ]
            ),
            decorators=[cst.Decorator(decorator=cst.Name("property"))],
        )

    def _create_property_setter(self) -> cst.FunctionDef:
        """Create property setter method.

        Returns:
            Property setter function definition
        """
        return cst.FunctionDef(
            name=cst.Name(self.field_name),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(name=cst.Name("value")),
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
        )


# Register the command
register_command(SelfEncapsulateFieldCommand)
