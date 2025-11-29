"""Replace Inheritance with Delegation refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter


class ReplaceInheritanceWithDelegationCommand(BaseCommand):
    """Convert a subclass to use delegation instead of inheriting from its superclass.

    Replace Inheritance with Delegation is a refactoring pattern that converts a subclass
    that only uses part of its superclass interface (or doesn't want to inherit data) into
    a standalone class that delegates to an instance of the superclass. This is useful when
    a subclass has become too different from its parent, doesn't need most of the inherited
    functionality, or when you want to change the behavior without being constrained by
    inheritance rules.

    This refactoring:
    - Removes the inheritance relationship (removes the superclass from bases)
    - Creates a field (typically named _items) to hold an instance of the former superclass
    - Adjusts methods to delegate to this field instead of using inherited behavior
    - Transforms super() calls to call methods on the delegate field

    **When to use:**
    - A subclass only uses a small part of its superclass interface
    - A subclass shouldn't inherit all the data members of its superclass
    - You want to change behavior that inheritance would prevent you from doing
    - The relationship between classes is "has-a" rather than "is-a"
    - You're working with list subclasses that should delegate to the underlying list

    **Example:**
    Before:
        class PricedItem(list):
            def __init__(self):
                super().__init__()
                self.price = 0

            def add_item(self, item):
                self.append(item)

            def get_total(self):
                return sum(item.price for item in self)

    After:
        class PricedItem:
            def __init__(self):
                self._items = []
                self.price = 0

            def add_item(self, item):
                self._items.append(item)

            def get_total(self):
                return sum(item.price for item in self._items)
    """

    name = "replace-inheritance-with-delegation"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

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
        self.original_init: cst.FunctionDef | None = None
        self.delegate_field_name: str = "_items"  # Default to _items

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to find superclass and original init."""
        if node.name.value == self.class_name:
            # Find the superclass from the bases
            for base in node.bases:
                if isinstance(base.value, cst.Name):
                    self.superclass_name = base.value.value
                    break

            # Find the original __init__ method
            for stmt in node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                    self.original_init = stmt
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

        # Create __init__ method with _items field and preserved instance variables
        init_method = self._create_init_method(original_node)

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

    def _create_init_method(self, class_node: cst.ClassDef) -> cst.FunctionDef:
        """Create __init__ method with _items field and preserved instance variables.

        Args:
            class_node: The class definition to extract parameters and assignments from

        Returns:
            The __init__ method
        """
        # Extract parameters and body statements from original __init__
        params = [create_parameter("self")]
        body_stmts: list[cst.BaseStatement] = []

        if self.original_init:
            # Copy parameters except self
            for param in self.original_init.params.params:
                if param.name.value != "self":
                    params.append(param)

            # Copy body statements that don't call super().__init__()
            if isinstance(self.original_init.body, cst.IndentedBlock):
                for stmt in self.original_init.body.body:
                    # Skip super().__init__() calls
                    if self._is_super_init_call(stmt):
                        continue
                    body_stmts.append(stmt)

        # Create: self._items = [] or self._data = {}
        # Determine the type and field name based on superclass
        if self.superclass_name == "dict":
            delegate_value: cst.BaseExpression = cst.Dict([])
            delegate_field_name = "_data"
        else:
            delegate_value = cst.List([])
            delegate_field_name = "_items"

        delegate_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name("self"), attr=cst.Name(delegate_field_name)
                            )
                        )
                    ],
                    value=delegate_value,
                )
            ]
        )

        # Store for later use in method transformation
        self.delegate_field_name = delegate_field_name

        # Combine: delegate assignment first, then other assignments
        final_body = [delegate_assignment] + body_stmts

        # Create __init__ method
        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=params),
            body=cst.IndentedBlock(body=final_body),
        )

        return init_method

    def _is_super_init_call(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a super().__init__() call.

        Args:
            stmt: The statement to check

        Returns:
            True if the statement calls super().__init__()
        """
        if isinstance(stmt, cst.SimpleStatementLine):
            for item in stmt.body:
                if isinstance(item, cst.Expr):
                    if isinstance(item.value, cst.Call):
                        call = item.value
                        if isinstance(call.func, cst.Attribute):
                            if isinstance(call.func.value, cst.Call):
                                if isinstance(call.func.value.func, cst.Name):
                                    if call.func.value.func.value == "super":
                                        return True
        return False

    def _transform_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a method to use delegation.

        Args:
            method: The method to transform

        Returns:
            The transformed method
        """
        # Transform super() calls and inherited method calls to use the delegate field
        transformer = DelegationTransformer(self.delegate_field_name)
        transformed = method.visit(transformer)
        if not isinstance(transformed, cst.FunctionDef):
            return method  # Return original if transformation failed
        return transformed


class DelegationTransformer(cst.CSTTransformer):
    """Transform inherited method calls to delegation calls.

    Transforms method calls that rely on inherited behavior to use a delegate field:
    - self.method() -> self._field.method() for inherited methods
    - super().method() -> self._field.method() for explicit super calls
    - len(self) -> len(self._field) for len built-in
    - self[key] -> self._field[key] for subscript access
    """

    # List of inherited methods that need delegation (list and dict methods)
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
            "get",
            "keys",
            "values",
            "items",
        ]
    )

    def __init__(self, delegate_field_name: str = "_items") -> None:
        """Initialize the transformer.

        Args:
            delegate_field_name: The name of the delegate field (e.g., "_items" or "_data")
        """
        self.delegate_field_name = delegate_field_name

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Transform super() and inherited method calls."""
        # Try to transform len(self) -> len(self._data)
        transformed = self._transform_len_call(updated_node)
        if transformed is not None:
            return transformed

        # Try to transform super().method() -> self._data.method()
        transformed = self._transform_super_call(updated_node)
        if transformed is not None:
            return transformed

        # Try to transform self.method() -> self._data.method()
        transformed = self._transform_delegated_method_call(updated_node)
        if transformed is not None:
            return transformed

        return updated_node

    def leave_Subscript(  # noqa: N802
        self, original_node: cst.Subscript, updated_node: cst.Subscript
    ) -> cst.BaseExpression:
        """Transform self[key] -> self._field[key]."""
        # Check if this is self[...] access
        if not isinstance(updated_node.value, cst.Name) or updated_node.value.value != "self":
            return updated_node

        # Transform to self._field[...]
        return updated_node.with_changes(
            value=cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.delegate_field_name))
        )

    def _transform_len_call(self, node: cst.Call) -> cst.Call | None:
        """Transform len(self) -> len(self._field).

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
            args=[
                cst.Arg(
                    value=cst.Attribute(
                        value=cst.Name("self"), attr=cst.Name(self.delegate_field_name)
                    )
                )
            ],
        )

    def _transform_super_call(self, node: cst.Call) -> cst.Call | None:
        """Transform super().method() -> self._field.method().

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
                value=cst.Attribute(
                    value=cst.Name("self"), attr=cst.Name(self.delegate_field_name)
                ),
                attr=cst.Name(method_name),
            ),
            args=node.args,
        )

    def _transform_delegated_method_call(self, node: cst.Call) -> cst.Call | None:
        """Transform self.method() -> self._field.method() for inherited methods.

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
                value=cst.Attribute(
                    value=cst.Name("self"), attr=cst.Name(self.delegate_field_name)
                ),
                attr=cst.Name(method_name),
            ),
            args=node.args,
        )


# Register the command
register_command(ReplaceInheritanceWithDelegationCommand)
