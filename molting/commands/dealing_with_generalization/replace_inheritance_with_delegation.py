"""Replace Inheritance with Delegation refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter


class ReplaceInheritanceWithDelegationCommand(BaseCommand):
    """Command to convert inheritance to delegation."""

    name = "replace-inheritance-with-delegation"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for replace-inheritance-with-delegation: 'target'"
            )

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
            raise ValueError(
                f"Class '{self.class_name}' does not inherit from any superclass. "
                "Replace Inheritance with Delegation requires a parent class."
            )

        # Remove inheritance
        new_bases: list[cst.Arg] = []

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
            new_body_stmts.append(stmt)  # type: ignore[arg-type]

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
                params=[create_parameter("self")],
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
        transformed = method.visit(transformer)
        if not isinstance(transformed, cst.FunctionDef):
            return method  # Return original if transformation failed
        return transformed


class DelegationTransformer(cst.CSTTransformer):
    """Transform inherited method calls to delegation calls.

    Transforms method calls that rely on inherited behavior to use a delegate field:
    - self.method() -> self._items.method() for inherited list methods
    - super().method() -> self._items.method() for explicit super calls
    - len(self) -> len(self._items) for len built-in
    """

    # List of inherited list methods that need delegation
    DELEGATED_METHODS = frozenset(
        [
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
        ]
    )

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Transform super() and inherited method calls."""
        # Try to transform len(self) -> len(self._items)
        transformed = self._transform_len_call(updated_node)
        if transformed is not None:
            return transformed

        # Try to transform super().method() -> self._items.method()
        transformed = self._transform_super_call(updated_node)
        if transformed is not None:
            return transformed

        # Try to transform self.method() -> self._items.method()
        transformed = self._transform_delegated_method_call(updated_node)
        if transformed is not None:
            return transformed

        return updated_node

    def _transform_len_call(self, node: cst.Call) -> cst.Call | None:
        """Transform len(self) -> len(self._items).

        Args:
            node: Call node to potentially transform

        Returns:
            Transformed call node or None if not applicable
        """
        if not (isinstance(node.func, cst.Name) and node.func.value == "len"):
            return None
        if len(node.args) != 1:
            return None
        arg = node.args[0]
        if not (isinstance(arg.value, cst.Name) and arg.value.value == "self"):
            return None

        return cst.Call(
            func=cst.Name("len"),
            args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("_items")))],
        )

    def _transform_super_call(self, node: cst.Call) -> cst.Call | None:
        """Transform super().method() -> self._items.method().

        Args:
            node: Call node to potentially transform

        Returns:
            Transformed call node or None if not applicable
        """
        if not isinstance(node.func, cst.Attribute):
            return None
        if not isinstance(node.func.value, cst.Call):
            return None
        if not isinstance(node.func.value.func, cst.Name):
            return None
        if node.func.value.func.value != "super":
            return None

        method_name = node.func.attr.value
        return cst.Call(
            func=cst.Attribute(
                value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("_items")),
                attr=cst.Name(method_name),
            ),
            args=node.args,
        )

    def _transform_delegated_method_call(self, node: cst.Call) -> cst.Call | None:
        """Transform self.method() -> self._items.method() for list methods.

        Args:
            node: Call node to potentially transform

        Returns:
            Transformed call node or None if not applicable
        """
        if not isinstance(node.func, cst.Attribute):
            return None
        if not isinstance(node.func.value, cst.Name):
            return None
        if node.func.value.value != "self":
            return None

        method_name = node.func.attr.value
        if method_name not in self.DELEGATED_METHODS:
            return None

        return cst.Call(
            func=cst.Attribute(
                value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("_items")),
                attr=cst.Name(method_name),
            ),
            args=node.args,
        )


# Register the command
register_command(ReplaceInheritanceWithDelegationCommand)
