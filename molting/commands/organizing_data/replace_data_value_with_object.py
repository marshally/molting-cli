"""Replace Data Value with Object refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, parse_target
from molting.core.call_site_updater import CallSiteUpdater, Reference
from molting.core.code_generation_utils import create_parameter
from molting.core.name_conflict_validator import NameConflictValidator
from molting.core.symbol_context import SymbolContext

INIT_METHOD_NAME = "__init__"


class ReplaceDataValueWithObjectCommand(BaseCommand):
    """Replace a data value with a proper object.

    This refactoring transforms a primitive value (such as a string or number)
    into a dedicated class when the data needs additional behavior or attributes.
    As code evolves, simple data items often require additional functionality like
    formatting, validation, or related properties that are better encapsulated in
    a dedicated class.

    **When to use:**
    - A primitive field needs specialized behavior (formatting, validation)
    - Related data items should be grouped together
    - You want to make the code's intent clearer
    - A data item appears in multiple places and needs consistent handling
    - You need to add constraints or rules to the data

    **Example:**
    Before:
        class Customer:
            def __init__(self, customer_name):
                self.name = customer_name

            def get_greeting(self):
                return f"Hello, {self.name}"

    After:
        class Name:
            def __init__(self, name):
                self.name = name

        class Customer:
            def __init__(self, customer_name):
                self.name = Name(customer_name)

            def get_greeting(self):
                return f"Hello, {self.name.name}"
    """

    name = "replace-data-value-with-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

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

        # Check for name conflicts before applying transformation
        validator = NameConflictValidator(source_code)
        validator.validate_class_name(new_class_name)

        module = cst.parse_module(source_code)

        transformer = ReplaceDataValueWithObjectTransformer(class_name, field_name, new_class_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)

        # Update call sites for the replaced field
        # External references to obj.field_name should become obj.field_name.name
        # But skip references within the target class (already transformed)
        param_name = transformer.param_name or "name"
        directory = self.file_path.parent
        updater = CallSiteUpdater(directory)
        self._update_field_access_sites(updater, field_name, param_name, class_name)

    def _update_field_access_sites(
        self, updater: CallSiteUpdater, field_name: str, param_name: str, class_name: str
    ) -> None:
        """Update all external access sites for the replaced field.

        Transforms: obj.field_name -> obj.field_name.param_name
        But only for references outside the target class (internal ones already transformed).

        Args:
            updater: The CallSiteUpdater to use
            field_name: Name of the field that was replaced
            param_name: Name of the parameter in the new class (e.g., "name")
            class_name: Name of the class containing the field (skip internal references)
        """

        def transform_access_site(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform field access to add the new object's attribute.

            Transforms: order.customer -> order.customer.name
            But only if it's not self.customer (those are handled by FieldAccessTransformer)
            """
            if isinstance(node, cst.Attribute):
                # Check if this is obj.field_name
                if node.attr.value == field_name:
                    # Skip if this is self.field_name (internal reference)
                    if isinstance(node.value, cst.Name) and node.value.value == "self":
                        return node
                    # Add the param_name attribute: obj.field_name.param_name
                    return cst.Attribute(value=node, attr=cst.Name(param_name))
            return node

        updater.update_all(field_name, SymbolContext.ATTRIBUTE_ACCESS, transform_access_site)


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
        self.param_name: str | None = None

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the new class to the module and modify the target class."""
        new_class = self._create_new_class()
        modified_statements: list[cst.BaseStatement] = []
        target_class = find_class_in_module(updated_node, self.class_name)

        # Check if the first statement is a module docstring
        has_docstring = False
        if (
            updated_node.body
            and isinstance(updated_node.body[0], cst.SimpleStatementLine)
            and updated_node.body[0].body
            and isinstance(updated_node.body[0].body[0], cst.Expr)
            and isinstance(
                updated_node.body[0].body[0].value, (cst.SimpleString, cst.ConcatenatedString)
            )
        ):
            has_docstring = True
            # Add the docstring first
            modified_statements.append(updated_node.body[0])
            # Add blank lines after docstring
            modified_statements.append(cast(cst.BaseStatement, cst.EmptyLine()))
            modified_statements.append(cast(cst.BaseStatement, cst.EmptyLine()))

        # Add the new class
        modified_statements.append(new_class)

        # Add the rest of the statements, skipping the docstring and inserting modified target class
        start_idx = 1 if has_docstring else 0
        for stmt in updated_node.body[start_idx:]:
            if stmt is target_class and isinstance(stmt, cst.ClassDef):
                modified_statements.append(self._modify_class(stmt))
            else:
                modified_statements.append(stmt)

        return updated_node.with_changes(body=tuple(modified_statements))

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
                if stmt.name.value == INIT_METHOD_NAME:
                    self._extract_parameter_name(stmt)
                    modified_init = self._modify_init_method(stmt)
                    new_body.append(modified_init)
                else:
                    modified_method = self._modify_method_body(stmt)
                    new_body.append(modified_method)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _extract_parameter_name(self, init_method: cst.FunctionDef) -> None:
        """Extract the parameter name for the field from __init__.

        Args:
            init_method: The __init__ method to analyze
        """
        if self.param_name is not None:
            return

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Attribute):
                                if (
                                    isinstance(target.target.value, cst.Name)
                                    and target.target.value.value == "self"
                                    and target.target.attr.value == self.field_name
                                ):
                                    if isinstance(body_item.value, cst.Name):
                                        assigned_param = body_item.value.value
                                        # Use simplified name for new class
                                        # e.g., customer_name -> name
                                        if assigned_param.endswith("_" + self.field_name):
                                            self.param_name = "name"
                                        elif assigned_param.startswith(self.field_name + "_"):
                                            self.param_name = "name"
                                        else:
                                            self.param_name = "name"
                                        return

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
                new_body_stmts.append(cast(cst.BaseStatement, stmt))

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
        param_name = self.param_name or "name"
        transformer = FieldAccessTransformer(self.field_name, param_name)
        new_method = method.visit(transformer)
        return cast(cst.FunctionDef, new_method)

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new class.

        Returns:
            New class definition
        """
        param_name = self.param_name or "name"

        init_method = cst.FunctionDef(
            name=cst.Name(INIT_METHOD_NAME),
            params=cst.Parameters(
                params=[
                    create_parameter("self"),
                    create_parameter(param_name),
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

    def __init__(self, field_name: str, param_name: str) -> None:
        """Initialize the transformer.

        Args:
            field_name: The field name being replaced
            param_name: The parameter name in the new class
        """
        self.field_name = field_name
        self.param_name = param_name

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Transform self.field_name to self.field_name.param_name.

        Args:
            original_node: The original attribute node
            updated_node: The updated attribute node

        Returns:
            Transformed attribute node
        """
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "self" and updated_node.attr.value == self.field_name:
                return cst.Attribute(
                    value=updated_node,
                    attr=cst.Name(self.param_name),
                )

        return updated_node


# Register the command
register_command(ReplaceDataValueWithObjectCommand)
