"""Replace Inheritance with Delegation refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class ReplaceInheritanceWithDelegationCommand(BaseCommand):
    """Command to convert inheritance to delegation."""

    name = "replace-inheritance-with-delegation"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        try:
            _ = self.params["target"]
        except KeyError as e:
            raise ValueError(
                f"Missing required parameter for replace-inheritance-with-delegation: {e}"
            ) from e

    def execute(self) -> None:
        """Apply replace-inheritance-with-delegation refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]

        # Parse target to get class name
        class_name = parse_target(target, expected_parts=1)[0]

        # Read file
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Apply transformation
        transformer = ReplaceInheritanceTransformer(class_name)
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ReplaceInheritanceTransformer(cst.CSTTransformer):
    """Transforms a class to use delegation instead of inheritance."""

    def __init__(self, class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to transform
        """
        self.class_name = class_name
        self.superclass_name: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to find superclass."""
        if node.name.value == self.class_name:
            # Find the superclass from the bases
            for base in node.bases:
                if isinstance(base.value, cst.Name):
                    self.superclass_name = base.value.value
                    break
        return True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and remove inheritance."""
        if original_node.name.value != self.class_name:
            return updated_node

        if not self.superclass_name:
            return updated_node

        # Remove inheritance
        new_bases = []

        # Create __init__ method with _items field
        init_method = self._create_init_method()

        # Update methods to use delegation
        new_body_stmts: list[cst.BaseStatement] = [init_method]
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                # Skip old __init__
                if stmt.name.value == "__init__":
                    continue
                # Transform methods to use delegation
                stmt = self._transform_method(stmt)
            new_body_stmts.append(stmt)

        return updated_node.with_changes(
            bases=new_bases, body=updated_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _create_init_method(self) -> cst.FunctionDef:
        """Create __init__ method with _items field.

        Returns:
            The __init__ method
        """
        # Create: self._items = []
        assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(value=cst.Name("self"), attr=cst.Name("_items"))
                        )
                    ],
                    value=cst.List([]),
                )
            ]
        )

        # Create __init__ method
        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))],
            ),
            body=cst.IndentedBlock(body=[assignment]),
        )

        return init_method

    def _transform_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a method to use delegation.

        Args:
            method: The method to transform

        Returns:
            The transformed method
        """
        # Transform super() calls and inherited method calls to use _items
        transformer = DelegationTransformer()
        return method.visit(transformer)


class DelegationTransformer(cst.CSTTransformer):
    """Transform inherited method calls to delegation calls."""

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Transform super() and inherited method calls."""
        # Handle len(self) -> len(self._items)
        if isinstance(updated_node.func, cst.Name) and updated_node.func.value == "len":
            if len(updated_node.args) == 1:
                arg = updated_node.args[0]
                if isinstance(arg.value, cst.Name) and arg.value.value == "self":
                    return cst.Call(
                        func=cst.Name("len"),
                        args=[
                            cst.Arg(
                                value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("_items"))
                            )
                        ],
                    )

        # Handle super().method() -> self._items.method()
        if isinstance(updated_node.func, cst.Attribute):
            if isinstance(updated_node.func.value, cst.Call):
                if isinstance(updated_node.func.value.func, cst.Name):
                    if updated_node.func.value.func.value == "super":
                        method_name = updated_node.func.attr.value
                        return cst.Call(
                            func=cst.Attribute(
                                value=cst.Attribute(
                                    value=cst.Name("self"), attr=cst.Name("_items")
                                ),
                                attr=cst.Name(method_name),
                            ),
                            args=updated_node.args,
                        )

            # Handle self.method() -> self._items.method() for list methods
            if isinstance(updated_node.func, cst.Attribute):
                if isinstance(updated_node.func.value, cst.Name):
                    if updated_node.func.value.value == "self":
                        method_name = updated_node.func.attr.value
                        if method_name in [
                            "append",
                            "pop",
                            "extend",
                            "insert",
                            "remove",
                            "clear",
                            "copy",
                            "count",
                            "index",
                            "reverse",
                            "sort",
                        ]:
                            return cst.Call(
                                func=cst.Attribute(
                                    value=cst.Attribute(
                                        value=cst.Name("self"), attr=cst.Name("_items")
                                    ),
                                    attr=cst.Name(method_name),
                                ),
                                args=updated_node.args,
                            )

        return updated_node


# Register the command
register_command(ReplaceInheritanceWithDelegationCommand)
