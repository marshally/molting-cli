"""Replace Type Code with Class refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, parse_target
from molting.core.code_generation_utils import create_parameter

INIT_METHOD_NAME = "__init__"


class ReplaceTypeCodeWithClassCommand(BaseCommand):
    """Command to replace type code constants with a new class."""

    name = "replace-type-code-with-class"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for replace-type-code-with-class: 'target'"
            )
        if "name" not in self.params:
            raise ValueError("Missing required parameter for replace-type-code-with-class: 'name'")

    def execute(self) -> None:
        """Apply replace-type-code-with-class refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        new_class_name = self.params["name"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ReplaceTypeCodeWithClassTransformer(class_name, field_name, new_class_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceTypeCodeWithClassTransformer(cst.CSTTransformer):
    """Transforms type code constants into a new class."""

    def __init__(self, class_name: str, field_name: str, new_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the type codes
            field_name: Name of the field using the type codes
            new_class_name: Name of the new class to create
        """
        self.class_name = class_name
        self.field_name = field_name
        self.new_class_name = new_class_name
        self.type_codes: list[tuple[str, cst.BaseExpression]] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to collect type codes before transformation.

        Args:
            node: The class definition node
        """
        if node.name.value == self.class_name:
            # Collect type codes from class variable assignments
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for body_item in stmt.body:
                        if isinstance(body_item, cst.Assign):
                            for target in body_item.targets:
                                if isinstance(target.target, cst.Name):
                                    # Store the type code for later
                                    self.type_codes.append((target.target.value, body_item.value))

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the new class to the module and modify the target class."""
        new_class = self._create_new_class()

        # Create class attribute assignments
        class_attributes: list[cst.BaseStatement] = []
        for code_name, code_value in self.type_codes:
            assignment = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Name(self.new_class_name),
                                    attr=cst.Name(code_name),
                                )
                            )
                        ],
                        value=cst.Call(
                            func=cst.Name(self.new_class_name),
                            args=[cst.Arg(value=code_value)],
                        ),
                    )
                ]
            )
            class_attributes.append(assignment)

        modified_statements: list[cst.BaseStatement] = [
            new_class,
            cast(cst.BaseStatement, cst.EmptyLine()),
        ]
        modified_statements.extend(class_attributes)
        modified_statements.append(cast(cst.BaseStatement, cst.EmptyLine()))

        target_class = find_class_in_module(updated_node, self.class_name)
        for stmt in updated_node.body:
            if stmt is target_class and isinstance(stmt, cst.ClassDef):
                modified_statements.append(self._modify_class(stmt))
            else:
                modified_statements.append(stmt)

        return updated_node.with_changes(body=tuple(modified_statements))

    def _modify_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Remove type code constants from the original class.

        Args:
            class_def: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Filter out class variable assignments that are type codes
                is_type_code = False
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Name):
                                # Check if this is a type code (already collected)
                                for code_name, _ in self.type_codes:
                                    if target.target.value == code_name:
                                        is_type_code = True
                                        break
                if not is_type_code:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new type code class.

        Returns:
            New class definition
        """
        init_method = cst.FunctionDef(
            name=cst.Name(INIT_METHOD_NAME),
            params=cst.Parameters(
                params=[
                    create_parameter("self"),
                    create_parameter("code"),
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
                                            attr=cst.Name("_code"),
                                        )
                                    )
                                ],
                                value=cst.Name("code"),
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


# Register the command
register_command(ReplaceTypeCodeWithClassCommand)
