"""Encapsulate Collection refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.call_site_updater import CallSiteUpdater, Reference
from molting.core.code_generation_utils import create_parameter
from molting.core.symbol_context import SymbolContext

SELF = "self"
INIT_METHOD = "__init__"
APPEND_METHOD = "append"
REMOVE_METHOD = "remove"
TUPLE_FUNCTION = "tuple"


class EncapsulateCollectionCommand(BaseCommand):
    """Encapsulates a collection field to prevent direct client modification.

    This refactoring transforms a public collection field into a private field with
    controlled access. The method that returned the collection is modified to return
    a read-only view (immutable tuple), and new add/remove methods are introduced
    to provide the only way for clients to modify the collection. This prevents
    accidental or unintended modifications and makes the object's invariants easier
    to maintain.

    **When to use:**
    - When a class has a public collection that clients modify directly
    - When you want to enforce stricter control over collection modifications
    - When adding logic to validate elements being added or removed
    - When you need to maintain class invariants related to the collection
    - To reduce coupling between the class and its clients

    **Example:**
    Before:
        class Person:
            def __init__(self, name):
                self.name = name
                self.items = []

            def get_items(self):
                return self.items

        # Client code can modify directly
        person = Person("Alice")
        person.items.append("item1")
        person.get_items().clear()  # Unwanted modification

    After:
        class Person:
            def __init__(self, name):
                self.name = name
                self._items = []

            def get_items(self):
                return tuple(self._items)  # Read-only view

            def add_item(self, item):
                self._items.append(item)

            def remove_item(self, item):
                self._items.remove(item)

        # Client code must use add/remove methods
        person = Person("Alice")
        person.add_item("item1")
        # person.get_items().clear()  # Now raises AttributeError
    """

    name = "encapsulate-collection"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply encapsulate-collection refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = EncapsulateCollectionTransformer(class_name, field_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)

        # Update call sites for the encapsulated field
        # External references to obj.field_name should become obj.get_field_name()
        directory = self.file_path.parent
        updater = CallSiteUpdater(directory)
        getter_name = f"get_{field_name}"
        self._update_field_access_sites(updater, field_name, getter_name, class_name)

    def _update_field_access_sites(
        self, updater: CallSiteUpdater, field_name: str, getter_name: str, class_name: str
    ) -> None:
        """Update all external access sites for the encapsulated field.

        Transforms: obj.field_name -> obj.get_field_name()
        But only for references outside the target class (internal ones already use private field).

        Args:
            updater: The CallSiteUpdater to use
            field_name: Name of the field that was encapsulated
            getter_name: Name of the getter method (e.g., "get_courses")
            class_name: Name of the class containing the field (skip internal references)
        """

        def transform_access_site(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform field access to a getter method call.

            Transforms: person.courses -> person.get_courses()
            But only if it's not self.courses (those use private field)
            """
            if isinstance(node, cst.Attribute):
                # Check if this is obj.field_name
                if node.attr.value == field_name:
                    # Skip if this is self.field_name (internal reference)
                    if isinstance(node.value, cst.Name) and node.value.value == "self":
                        return node
                    # Transform to obj.get_field_name()
                    return cst.Call(
                        func=cst.Attribute(value=node.value, attr=cst.Name(getter_name)),
                        args=[],
                    )
            return node

        updater.update_all(field_name, SymbolContext.ATTRIBUTE_ACCESS, transform_access_site)


class EncapsulateCollectionTransformer(cst.CSTTransformer):
    """Transforms a collection field to be properly encapsulated."""

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the field
            field_name: Name of the collection field to encapsulate
        """
        self.class_name = class_name
        self.field_name = field_name
        self.private_field_name = f"_{field_name}"
        self.singular_name = self._derive_singular_name(field_name)

    def _derive_singular_name(self, field_name: str) -> str:
        """Derive singular name from plural field name.

        Args:
            field_name: The plural field name

        Returns:
            Singular form of the field name
        """
        return field_name.rstrip("s")

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Modify the class to encapsulate the collection.

        Args:
            original_node: The original class definition
            updated_node: The updated class definition

        Returns:
            Modified class definition
        """
        if updated_node.name.value != self.class_name:
            return updated_node

        new_body: list[cst.BaseStatement] = []

        # First pass: modify existing methods
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD:
                    new_body.append(self._modify_init_method(stmt))
                elif stmt.name.value == f"get_{self.field_name}":
                    new_body.append(self._modify_getter_method(stmt))
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # Second pass: add add/remove methods
        new_body.append(self._create_add_method())
        new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
        new_body.append(self._create_remove_method())

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_init_method(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify __init__ to use private field name.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in init_method.body.body:
            modified_stmt = self._try_modify_field_assignment(cast(cst.BaseStatement, stmt))
            new_body.append(
                modified_stmt if modified_stmt is not None else cast(cst.BaseStatement, stmt)
            )

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _try_modify_field_assignment(self, stmt: cst.BaseStatement) -> cst.BaseStatement | None:
        """Try to modify a statement that assigns to the target field.

        Args:
            stmt: Statement to potentially modify

        Returns:
            Modified statement if it assigns to target field, None otherwise
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return None

        for body_item in stmt.body:
            if not isinstance(body_item, cst.Assign):
                continue

            for target in body_item.targets:
                if self._is_field_assignment(target.target):
                    return self._create_private_field_assignment(body_item.value)

        return None

    def _is_field_assignment(self, target: cst.BaseExpression) -> bool:
        """Check if target is an assignment to self.field_name.

        Args:
            target: Assignment target to check

        Returns:
            True if target is self.field_name
        """
        if not isinstance(target, cst.Attribute):
            return False

        return (
            isinstance(target.value, cst.Name)
            and target.value.value == SELF
            and target.attr.value == self.field_name
        )

    def _create_private_field_assignment(
        self, value: cst.BaseExpression
    ) -> cst.SimpleStatementLine:
        """Create assignment to private field.

        Args:
            value: Value to assign

        Returns:
            Assignment statement for private field
        """
        return cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name(SELF),
                                attr=cst.Name(self.private_field_name),
                            )
                        )
                    ],
                    value=value,
                )
            ]
        )

    def _modify_getter_method(self, getter_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify getter to return a read-only view.

        Args:
            getter_method: The getter method

        Returns:
            Modified getter method
        """
        new_return = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Call(
                        func=cst.Name(TUPLE_FUNCTION),
                        args=[
                            cst.Arg(
                                value=cst.Attribute(
                                    value=cst.Name(SELF), attr=cst.Name(self.private_field_name)
                                )
                            )
                        ],
                    )
                )
            ]
        )

        return getter_method.with_changes(body=cst.IndentedBlock(body=[new_return]))

    def _create_add_method(self) -> cst.FunctionDef:
        """Create add_<field> method.

        Returns:
            New add method
        """
        return cst.FunctionDef(
            name=cst.Name(f"add_{self.singular_name}"),
            params=cst.Parameters(
                params=[
                    create_parameter(SELF),
                    create_parameter(self.singular_name),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name(SELF),
                                            attr=cst.Name(self.private_field_name),
                                        ),
                                        attr=cst.Name(APPEND_METHOD),
                                    ),
                                    args=[cst.Arg(value=cst.Name(self.singular_name))],
                                )
                            )
                        ]
                    )
                ]
            ),
        )

    def _create_remove_method(self) -> cst.FunctionDef:
        """Create remove_<field> method.

        Returns:
            New remove method
        """
        return cst.FunctionDef(
            name=cst.Name(f"remove_{self.singular_name}"),
            params=cst.Parameters(
                params=[
                    create_parameter(SELF),
                    create_parameter(self.singular_name),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name(SELF),
                                            attr=cst.Name(self.private_field_name),
                                        ),
                                        attr=cst.Name(REMOVE_METHOD),
                                    ),
                                    args=[cst.Arg(value=cst.Name(self.singular_name))],
                                )
                            )
                        ]
                    )
                ]
            ),
        )


# Register the command
register_command(EncapsulateCollectionCommand)
