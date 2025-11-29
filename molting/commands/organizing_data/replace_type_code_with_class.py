"""Replace Type Code with Class refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter
from molting.core.name_conflict_validator import NameConflictValidator

INIT_METHOD_NAME = "__init__"


class ReplaceTypeCodeWithClassCommand(BaseCommand):
    """Replace a numeric or string type code with a proper class.

    This refactoring replaces numeric or string type codes (constants used to
    distinguish between different types or categories) with a dedicated class.
    Type codes are often represented as magic numbers or strings scattered
    throughout a codebase, making code harder to understand and more prone to
    errors.

    **When to use:**
    - When you have magic numbers or strings representing different types or categories
    - When you need to add type safety and compiler/type checker support
    - When you want to add behavior (methods) that depend on the type
    - When type codes are used across multiple classes and need centralization
    - When you want to make implicit types explicit in the code

    **Example:**
    Before:
        class Patient:
            BLOOD_TYPE_O = 0
            BLOOD_TYPE_A = 1
            BLOOD_TYPE_B = 2
            BLOOD_TYPE_AB = 3

            def __init__(self, name: str, blood_type: int):
                self.name = name
                self.blood_type = blood_type

    After:
        class BloodType:
            def __init__(self, code: int):
                self._code = code

        BloodType.O = BloodType(0)
        BloodType.A = BloodType(1)
        BloodType.B = BloodType(2)
        BloodType.AB = BloodType(3)

        class Patient:
            def __init__(self, name: str, blood_type: BloodType):
                self.name = name
                self.blood_type = blood_type
    """

    name = "replace-type-code-with-class"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

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

        # Check for name conflicts before applying transformation
        validator = NameConflictValidator(source_code)
        validator.validate_class_name(new_class_name)

        module = cst.parse_module(source_code)

        transformer = ReplaceTypeCodeWithClassTransformer(class_name, field_name, new_class_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceTypeCodeWithClassTransformer(cst.CSTTransformer):
    """Transforms type codes into a class."""

    def __init__(self, class_name: str, field_name: str, new_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the type codes
            field_name: Name of the field that uses the type code
            new_class_name: Name of the new class to create
        """
        self.class_name = class_name
        self.field_name = field_name
        self.new_class_name = new_class_name
        self.type_codes: list[tuple[str, int]] = []

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the new class to the module and modify the target class."""
        # First pass: extract type codes from the target class
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.class_name:
                self._extract_type_codes(stmt)
                break

        # Create the new type code class
        new_class = self._create_type_code_class()

        # Create class-level instances
        instance_assignments = self._create_class_instances()

        # Build the new module structure
        modified_statements: list[cst.BaseStatement] = [
            new_class,
        ]

        # Add instance assignments
        for assignment in instance_assignments:
            modified_statements.append(assignment)

        # Add empty lines for separation
        modified_statements.extend(
            [
                cast(cst.BaseStatement, cst.EmptyLine()),
                cast(cst.BaseStatement, cst.EmptyLine()),
            ]
        )

        # Add the modified original class
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.class_name:
                modified_class = self._modify_class(stmt)
                modified_statements.append(modified_class)
            else:
                modified_statements.append(stmt)

        return updated_node.with_changes(body=tuple(modified_statements))

    def _extract_type_codes(self, class_def: cst.ClassDef) -> None:
        """Extract type codes from the class.

        Args:
            class_def: The class definition to analyze
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Name):
                                # Check if this is a type code assignment
                                if isinstance(body_item.value, cst.Integer):
                                    # Store for later use
                                    name = target.target.value
                                    value = int(body_item.value.value)
                                    self.type_codes.append((name, value))

    def _modify_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the original class to remove type codes.

        Args:
            class_def: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []
        type_code_names = {name for name, _ in self.type_codes}

        for stmt in class_def.body.body:
            # Skip class variable assignments (type codes)
            if isinstance(stmt, cst.SimpleStatementLine):
                skip_stmt = False
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Name):
                                # Check if this is a type code assignment
                                if target.target.value in type_code_names:
                                    skip_stmt = True
                                    break
                if not skip_stmt:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_type_code_class(self) -> cst.ClassDef:
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

    def _create_class_instances(self) -> list[cst.SimpleStatementLine]:
        """Create class-level instance assignments.

        Returns:
            List of assignment statements
        """
        assignments: list[cst.SimpleStatementLine] = []

        for name, value in self.type_codes:
            # Create: BloodGroup.O = BloodGroup(0)
            assignment = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Name(self.new_class_name),
                                    attr=cst.Name(name),
                                )
                            )
                        ],
                        value=cst.Call(
                            func=cst.Name(self.new_class_name),
                            args=[cst.Arg(value=cst.Integer(str(value)))],
                        ),
                    )
                ]
            )
            assignments.append(assignment)

        return assignments


# Register the command
register_command(ReplaceTypeCodeWithClassCommand)
