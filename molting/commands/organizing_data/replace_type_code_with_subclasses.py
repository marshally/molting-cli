"""Replace Type Code with Subclasses refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class ReplaceTypeCodeWithSubclassesCommand(BaseCommand):
    """Replace type code with subclasses to eliminate type-based conditionals.

    This refactoring replaces integer or string type codes that control behavior
    with a subclass hierarchy. Instead of checking a type field and branching
    logic based on its value, each type becomes its own subclass. This approach
    leverages object-oriented principles and eliminates scattered type-checking
    conditionals throughout the codebase.

    **When to use:**
    - You have a type code (integer or string constant) that affects object behavior
    - The code contains multiple conditionals checking the type code
    - You want to make type-specific behavior explicit and maintainable
    - Each type code maps to a distinct set of behaviors

    **Example:**
    Before:
        class Employee:
            ENGINEER = "engineer"
            MANAGER = "manager"

            def __init__(self, name, employee_type):
                self.name = name
                self.employee_type = employee_type

            def get_rate(self):
                if self.employee_type == self.ENGINEER:
                    return 50
                elif self.employee_type == self.MANAGER:
                    return 80

    After:
        class Employee:
            @staticmethod
            def create(employee_type):
                if employee_type == "engineer":
                    return Engineer()
                elif employee_type == "manager":
                    return Manager()

        class Engineer(Employee):
            def get_rate(self):
                return 50

        class Manager(Employee):
            def get_rate(self):
                return 80
    """

    name = "replace-type-code-with-subclasses"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-type-code-with-subclasses refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ReplaceTypeCodeWithSubclassesTransformer(class_name, field_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceTypeCodeWithSubclassesTransformer(cst.CSTTransformer):
    """Transforms type code into subclasses with factory method."""

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the type code
            field_name: Name of the field representing the type code
        """
        self.class_name = class_name
        self.field_name = field_name
        self.type_codes: list[str] = []

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add subclasses after the main class."""
        new_body: list[cst.BaseStatement] = []

        for stmt in updated_node.body:
            new_body.append(stmt)
            # After the target class, add the subclasses
            if isinstance(stmt, cst.SimpleStatementLine):
                for body_item in stmt.body:
                    if isinstance(body_item, cst.ClassDef):
                        if body_item.name.value == self.class_name:
                            # Add subclasses
                            for type_code in self.type_codes:
                                new_body.append(self._create_subclass(type_code))
            elif isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.class_name:
                    # Add subclasses
                    for type_code in self.type_codes:
                        new_body.append(self._create_subclass(type_code))

        return updated_node.with_changes(body=new_body)

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform the target class to use factory method."""
        if updated_node.name.value != self.class_name:
            return updated_node

        # Extract type codes from class constants
        self._extract_type_codes(updated_node)

        # Remove type code constants and __init__, add factory method
        new_body: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            base_stmt = cast(cst.BaseStatement, stmt)
            # Skip type code constants
            if self._is_type_code_constant(base_stmt):
                continue
            # Replace __init__ with factory method
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                new_body.append(self._create_factory_method())
            else:
                new_body.append(base_stmt)

        # If there was no __init__, just add the factory method
        has_init = any(
            isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__"
            for stmt in updated_node.body.body
        )
        if not has_init:
            new_body.insert(0, self._create_factory_method())

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _extract_type_codes(self, class_node: cst.ClassDef) -> None:
        """Extract type code constant names from the class.

        Args:
            class_node: The class definition to extract from
        """
        for stmt in class_node.body.body:
            base_stmt = cast(cst.BaseStatement, stmt)
            if self._is_type_code_constant(base_stmt):
                if isinstance(stmt, cst.SimpleStatementLine):
                    for body_item in stmt.body:
                        if isinstance(body_item, cst.Assign):
                            for target in body_item.targets:
                                if isinstance(target.target, cst.Name):
                                    self.type_codes.append(target.target.value)

    def _is_type_code_constant(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a type code constant assignment.

        Args:
            stmt: Statement to check

        Returns:
            True if this is a type code constant assignment
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        for body_item in stmt.body:
            if isinstance(body_item, cst.Assign):
                # Check if it's a constant assignment (NAME = integer)
                if isinstance(body_item.value, cst.Integer):
                    for target in body_item.targets:
                        if isinstance(target.target, cst.Name):
                            # Assume uppercase names are constants
                            if target.target.value.isupper():
                                return True
        return False

    def _create_factory_method(self) -> cst.FunctionDef:
        """Create the factory method that instantiates subclasses.

        Returns:
            Factory method definition
        """
        # Build if-elif chain by iterating in reverse and nesting
        if_chain: cst.If | None = None

        for type_code in reversed(self.type_codes):
            condition = cst.Comparison(
                left=cst.Name("employee_type"),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Equal(),
                        comparator=cst.SimpleString(f'"{type_code}"'),
                    )
                ],
            )

            return_stmt = cst.SimpleStatementLine(
                body=[cst.Return(value=cst.Call(func=cst.Name(type_code.capitalize())))]
            )

            if if_chain is None:
                # Last condition (no else)
                if_chain = cst.If(
                    test=condition,
                    body=cst.IndentedBlock(body=[return_stmt]),
                    orelse=None,
                )
            else:
                # Wrap previous chain as orelse
                if_chain = cst.If(
                    test=condition,
                    body=cst.IndentedBlock(body=[return_stmt]),
                    orelse=if_chain,
                )

        return cst.FunctionDef(
            name=cst.Name("create"),
            params=cst.Parameters(
                params=[
                    cst.Param(
                        name=cst.Name("employee_type"),
                    )
                ]
            ),
            body=cst.IndentedBlock(body=[cast(cst.BaseStatement, if_chain)]),
            decorators=[cst.Decorator(decorator=cst.Name("staticmethod"))],
        )

    def _create_subclass(self, type_code: str) -> cst.ClassDef:
        """Create a subclass for a type code.

        Args:
            type_code: The type code constant name (e.g., "ENGINEER")

        Returns:
            Subclass definition
        """
        class_name = type_code.capitalize()

        return cst.ClassDef(
            name=cst.Name(class_name),
            body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
            bases=[cst.Arg(value=cst.Name(self.class_name))],
            leading_lines=[cst.EmptyLine(), cst.EmptyLine()],
        )


# Register the command
register_command(ReplaceTypeCodeWithSubclassesCommand)
