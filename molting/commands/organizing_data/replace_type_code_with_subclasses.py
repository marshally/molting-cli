"""Replace Type Code with Subclasses refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, parse_target


class ReplaceTypeCodeWithSubclassesCommand(BaseCommand):
    """Command to replace type code with subclasses."""

    name = "replace-type-code-with-subclasses"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for replace-type-code-with-subclasses: 'target'"
            )

    def execute(self) -> None:
        """Apply replace-type-code-with-subclasses refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ReplaceTypeCodeWithSubclassesTransformer(class_name, field_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceTypeCodeWithSubclassesTransformer(cst.CSTTransformer):
    """Transforms type code into subclasses."""

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the type code
            field_name: Name of the field representing the type code
        """
        self.class_name = class_name
        self.field_name = field_name
        self.type_constants: dict[str, int] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definitions to find the target class and extract type constants.

        Args:
            node: The class definition node
        """
        if node.name.value == self.class_name:
            # Extract type constants
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for body_item in stmt.body:
                        if isinstance(body_item, cst.Assign):
                            for target in body_item.targets:
                                if isinstance(target.target, cst.Name):
                                    const_name = target.target.value
                                    if isinstance(body_item.value, cst.Integer):
                                        self.type_constants[const_name] = int(body_item.value.value)

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Transform the module by modifying the class and adding subclasses.

        Args:
            original_node: The original module node
            updated_node: The updated module node

        Returns:
            Modified module with subclasses
        """
        modified_statements: list[cst.BaseStatement] = []

        target_class = find_class_in_module(updated_node, self.class_name)
        for stmt in updated_node.body:
            if stmt is target_class and isinstance(stmt, cst.ClassDef):
                # Add modified base class
                modified_class = self._modify_base_class(stmt)
                modified_statements.append(modified_class)
                modified_statements.append(cast(cst.BaseStatement, cst.EmptyLine()))
                modified_statements.append(cast(cst.BaseStatement, cst.EmptyLine()))

                # Add subclasses (sorted by their numeric value)
                sorted_constants = sorted(self.type_constants.items(), key=lambda x: x[1])
                for const_name, _ in sorted_constants:
                    subclass = self._create_subclass(const_name)
                    modified_statements.append(subclass)
                    modified_statements.append(cast(cst.BaseStatement, cst.EmptyLine()))
                    modified_statements.append(cast(cst.BaseStatement, cst.EmptyLine()))
            else:
                modified_statements.append(stmt)

        return updated_node.with_changes(body=tuple(modified_statements))

    def _modify_base_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the base class to remove type constants and add factory method.

        Args:
            class_def: The class definition to modify

        Returns:
            Modified class definition
        """
        # Remove type constants and __init__ method
        new_body: list[cst.BaseStatement] = []

        # Add factory method
        factory_method = self._create_factory_method()
        new_body.append(factory_method)

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _convert_constant_to_class_name(self, const_name: str) -> str:
        """Convert a type constant name to a class name.

        Args:
            const_name: The constant name (e.g., ENGINEER)

        Returns:
            The class name (e.g., Engineer)
        """
        return const_name.title().replace("_", "")

    def _create_factory_method(self) -> cst.FunctionDef:
        """Create a static factory method.

        Returns:
            Factory method definition
        """
        # Build the if-elif chain (sorted by numeric value)
        sorted_constants = sorted(self.type_constants.items(), key=lambda x: x[1])

        # Build from the end backwards to properly chain the elif statements
        if_stmt = None
        for const_name, _ in reversed(sorted_constants):
            condition_test = cst.Comparison(
                left=cst.Name("employee_type"),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Equal(),
                        comparator=cst.SimpleString(f'"{const_name}"'),
                    )
                ],
            )

            return_stmt = cst.SimpleStatementLine(
                body=[
                    cst.Return(
                        value=cst.Call(
                            func=cst.Name(self._convert_constant_to_class_name(const_name)),
                            args=[],
                        )
                    )
                ]
            )

            if_stmt = cst.If(
                test=condition_test,
                body=cst.IndentedBlock(body=[return_stmt]),
                orelse=if_stmt,
            )

        factory_body = cst.IndentedBlock(body=[if_stmt])  # type: ignore

        return cst.FunctionDef(
            name=cst.Name("create"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("employee_type")),
                ]
            ),
            body=factory_body,
            decorators=[
                cst.Decorator(
                    decorator=cst.Name("staticmethod"),
                )
            ],
        )

    def _create_subclass(self, const_name: str) -> cst.ClassDef:
        """Create a subclass for the given type constant.

        Args:
            const_name: Name of the type constant

        Returns:
            Subclass definition
        """
        subclass_name = self._convert_constant_to_class_name(const_name)

        return cst.ClassDef(
            name=cst.Name(subclass_name),
            bases=[cst.Arg(value=cst.Name(self.class_name))],
            body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
        )


# Register the command
register_command(ReplaceTypeCodeWithSubclassesCommand)
