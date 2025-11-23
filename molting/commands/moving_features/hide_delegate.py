"""Hide Delegate refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class HideDelegateCommand(BaseCommand):
    """Command to hide a delegate by creating delegating methods."""

    name = "hide-delegate"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for hide-delegate: 'target'")

    def execute(self) -> None:
        """Apply hide-delegate refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]

        parts = target.split("::")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid target format: {target}. Expected format: ClassName::field_name"
            )

        class_name = parts[0]
        field_name = parts[1]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = HideDelegateTransformer(class_name, field_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class HideDelegateTransformer(cst.CSTTransformer):
    """Transforms classes to hide a delegate field."""

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the delegate field
            field_name: Name of the field to hide
        """
        self.class_name = class_name
        self.field_name = field_name

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and update as needed."""
        if original_node.name.value == self.class_name:
            return self._transform_class(updated_node)
        return updated_node

    def _transform_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the class to hide the delegate field."""
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                new_init = self._transform_init(stmt)
                new_body_stmts.append(new_init)
            else:
                new_body_stmts.append(stmt)

        new_body_stmts.append(self._create_delegating_method())

        return node.with_changes(body=node.body.with_changes(body=tuple(new_body_stmts)))

    def _transform_init(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform __init__ to make the field private."""
        new_stmts: list[cst.BaseStatement] = []

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    new_body_items = []
                    for item in stmt.body:
                        if isinstance(item, cst.Assign):
                            new_item = self._transform_assignment(item)
                            new_body_items.append(new_item)
                        else:
                            new_body_items.append(item)
                    new_stmts.append(stmt.with_changes(body=new_body_items))
                else:
                    new_stmts.append(stmt)

        return node.with_changes(body=cst.IndentedBlock(body=tuple(new_stmts)))

    def _transform_assignment(self, assign: cst.Assign) -> cst.Assign:
        """Transform assignment to make field private if it matches."""
        for target in assign.targets:
            if isinstance(target.target, cst.Attribute):
                if (
                    isinstance(target.target.value, cst.Name)
                    and target.target.value.value == "self"
                    and target.target.attr.value == self.field_name
                ):
                    new_target = cst.AssignTarget(
                        cst.Attribute(value=cst.Name("self"), attr=cst.Name(f"_{self.field_name}"))
                    )
                    return assign.with_changes(targets=[new_target])
        return assign

    def _create_delegating_method(self) -> cst.FunctionDef:
        """Create a delegating method for the hidden field."""
        return cst.FunctionDef(
            name=cst.Name("get_manager"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Attribute(
                                    value=cst.Attribute(
                                        value=cst.Name("self"), attr=cst.Name(f"_{self.field_name}")
                                    ),
                                    attr=cst.Name("manager"),
                                )
                            )
                        ]
                    )
                ]
            ),
        )


register_command(HideDelegateCommand)
