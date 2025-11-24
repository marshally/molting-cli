"""Extract Class refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import is_assignment_to_field, parse_comma_separated_list
from molting.core.code_generation_utils import create_parameter


class ExtractClassCommand(BaseCommand):
    """Command to extract a new class from an existing class."""

    name = "extract-class"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("source", "fields", "methods", "name")

    def execute(self) -> None:
        """Apply extract-class refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        source_class = self.params["source"]
        fields_str = self.params["fields"]
        methods_str = self.params["methods"]
        new_class_name = self.params["name"]

        fields = parse_comma_separated_list(fields_str)
        methods = parse_comma_separated_list(methods_str)

        self.apply_libcst_transform(
            ExtractClassTransformer, source_class, fields, methods, new_class_name
        )


class ExtractClassTransformer(cst.CSTTransformer):
    """Transformer to extract a new class from an existing class."""

    def __init__(
        self,
        source_class: str,
        fields: list[str],
        methods: list[str],
        new_class_name: str,
    ):
        """Initialize the transformer.

        Args:
            source_class: Name of the class to extract from
            fields: List of field names to extract
            methods: List of method names to extract
            new_class_name: Name of the new class to create
        """
        self.source_class = source_class
        self.fields = fields
        self.methods = methods
        self.new_class_name = new_class_name
        self.extracted_methods: list[cst.FunctionDef] = []

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.FlattenSentinel[cst.ClassDef]:
        """Transform the source class and create the new class.

        Args:
            original_node: The original class node
            updated_node: The updated class node

        Returns:
            The transformed class or a flattened sequence with both classes
        """
        if updated_node.name.value != self.source_class:
            return updated_node

        new_body: list[cst.BaseStatement] = []
        delegate_field_name = self._calculate_delegate_field_name()

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == "__init__":
                    modified_init = self._modify_init(stmt, delegate_field_name)
                    new_body.append(modified_init)
                elif stmt.name.value in self.methods:
                    self.extracted_methods.append(stmt)
                    delegate_method = self._create_delegate_method(stmt, delegate_field_name)
                    new_body.append(delegate_method)
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        updated_class = updated_node.with_changes(body=cst.IndentedBlock(body=new_body))
        new_class = self._create_new_class()

        return cst.FlattenSentinel(
            [
                updated_class,
                cast(cst.ClassDef, cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))),
                cast(cst.ClassDef, cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))),
                new_class,
            ]
        )

    def _calculate_delegate_field_name(self) -> str:
        """Calculate the name for the delegate field.

        Converts class name to snake_case and adds prefix.
        For example: TelephoneNumber -> office_telephone

        Returns:
            The delegate field name
        """
        base_name = self.new_class_name
        for suffix in ["Number", "Info", "Data", "Class"]:
            if base_name.endswith(suffix):
                base_name = base_name[: -len(suffix)]
                break
        delegate_field_name = (
            base_name[0].lower() + base_name[1:] if base_name else self.new_class_name.lower()
        )
        return f"office_{delegate_field_name.lower()}"

    def _modify_init(
        self, init_method: cst.FunctionDef, delegate_field_name: str
    ) -> cst.FunctionDef:
        """Modify the __init__ method to use delegation.

        Args:
            init_method: The original __init__ method
            delegate_field_name: Name of the field for the delegated object

        Returns:
            Modified __init__ method
        """
        extracted_param_names = []
        for param in init_method.params.params:
            if isinstance(param.name, cst.Name):
                if param.name.value in self.fields:
                    extracted_param_names.append(param.name.value)

        new_body_stmts: list[cst.BaseStatement] = []
        field_names_set = set(self.fields)
        for stmt in init_method.body.body:
            if not is_assignment_to_field(cast(cst.BaseStatement, stmt), field_names_set):
                new_body_stmts.append(cast(cst.BaseStatement, stmt))

        delegate_args = [
            cst.Arg(value=cst.Name(param_name)) for param_name in extracted_param_names
        ]
        delegate_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(delegate_field_name),
                            )
                        )
                    ],
                    value=cst.Call(func=cst.Name(self.new_class_name), args=delegate_args),
                )
            ]
        )
        new_body_stmts.append(delegate_assignment)

        return init_method.with_changes(
            body=cst.IndentedBlock(body=new_body_stmts),
        )

    def _create_delegate_method(
        self, method: cst.FunctionDef, delegate_field_name: str
    ) -> cst.FunctionDef:
        """Create a delegating method in the source class.

        Args:
            method: The original method
            delegate_field_name: Name of the field for the delegated object

        Returns:
            Delegating method
        """
        delegate_call = cst.Return(
            value=cst.Call(
                func=cst.Attribute(
                    value=cst.Attribute(value=cst.Name("self"), attr=cst.Name(delegate_field_name)),
                    attr=cst.Name(method.name.value),
                ),
                args=[],
            )
        )

        return method.with_changes(
            body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[delegate_call])])
        )

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new extracted class.

        Returns:
            The new class definition
        """
        param_mapping = {}
        for field in self.fields:
            if field.startswith("office_"):
                param_mapping[field] = field[7:]
            else:
                param_mapping[field] = field

        params = [create_parameter("self")] + [
            create_parameter(param_mapping[field]) for field in self.fields
        ]

        assignments = [
            cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(param_mapping[field]),
                                )
                            )
                        ],
                        value=cst.Name(param_mapping[field]),
                    )
                ]
            )
            for field in self.fields
        ]

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=params),
            body=cst.IndentedBlock(body=assignments),
        )

        updated_methods: list[cst.FunctionDef] = []
        for method in self.extracted_methods:
            transformer = FieldRenameTransformer(param_mapping)
            updated_method = method.visit(transformer)
            updated_methods.append(cast(cst.FunctionDef, updated_method))

        class_body: list[cst.BaseStatement] = [
            init_method,
            cast(cst.BaseStatement, cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))),
        ]
        for i, method in enumerate(updated_methods):
            class_body.append(method)
            if i < len(updated_methods) - 1:
                class_body.append(
                    cast(cst.BaseStatement, cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                )

        return cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[],
            body=cst.IndentedBlock(body=class_body),
        )


class FieldRenameTransformer(cst.CSTTransformer):
    """Transformer to rename fields in extracted methods."""

    def __init__(self, field_mapping: dict[str, str]):
        """Initialize the transformer.

        Args:
            field_mapping: Mapping from old field names to new field names
        """
        self.field_mapping = field_mapping

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Rename self.old_field to self.new_field.

        Args:
            original_node: The original attribute node
            updated_node: The updated attribute node

        Returns:
            The transformed attribute node
        """
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "self":
                if updated_node.attr.value in self.field_mapping:
                    new_name = self.field_mapping[updated_node.attr.value]
                    return updated_node.with_changes(attr=cst.Name(new_name))
        return updated_node


# Register the command
register_command(ExtractClassCommand)
