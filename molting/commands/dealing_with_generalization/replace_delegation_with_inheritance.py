"""Replace Delegation with Inheritance refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_class, parse_target


class ReplaceDelegationWithInheritanceCommand(BaseCommand):
    """Replace Delegation with Inheritance refactoring command.

    This refactoring converts a delegating class that delegates all its methods
    to a delegate object into a subclass of the delegate. When you find yourself
    writing many delegating methods that simply forward calls to a delegate
    object, this refactoring eliminates that boilerplate by making the delegating
    class inherit from the delegate instead.

    **When to use:**
    - You have a class that delegates to another class and uses all (or most) of its methods
    - The delegation methods are repetitive and add maintenance burden
    - The delegating class and delegate class have a genuine is-a relationship
    - You want to reduce boilerplate code while maintaining the same functionality

    **Example:**
    Before:
        class Person:
            def get_name(self):
                return self._delegate.get_name()

            def set_name(self, name):
                self._delegate.set_name(name)

            def age(self):
                return self._delegate.age()

    After:
        class Person(Delegate):
            def __init__(self, ...):
                super().__init__(...)
    """

    name = "replace-delegation-with-inheritance"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        try:
            _ = self.params["target"]
            _ = self.params["delegate"]
        except KeyError as e:
            raise ValueError(
                f"Missing required parameter for replace-delegation-with-inheritance: {e}"
            ) from e

    def execute(self) -> None:
        """Apply replace-delegation-with-inheritance refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        delegate_field = self.params["delegate"]

        # Parse target to get class name
        class_name = parse_target(target, expected_parts=1)[0]

        # Read file
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Apply transformation
        transformer = ReplaceDelegationTransformer(class_name, delegate_field)
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ReplaceDelegationTransformer(cst.CSTTransformer):
    """Transforms a class to inherit from delegate instead of delegating."""

    def __init__(self, class_name: str, delegate_field: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the delegating class
            delegate_field: Name of the delegate field
        """
        self.class_name = class_name
        self.delegate_field = delegate_field
        self.delegate_type: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to find delegate type."""
        if node.name.value == self.class_name:
            # Find the delegate field assignment to get the delegate class
            # Look in __init__ method first
            init_method = find_method_in_class(node, "__init__")
            if init_method:
                # Find the delegate assignment in __init__
                for init_stmt in init_method.body.body:
                    if isinstance(init_stmt, cst.SimpleStatementLine):
                        for item in init_stmt.body:
                            if isinstance(item, cst.Assign):
                                for target in item.targets:
                                    # Check for self._field = Class(...)
                                    if isinstance(target.target, cst.Attribute):
                                        if (
                                            isinstance(target.target.value, cst.Name)
                                            and target.target.value.value == "self"
                                            and target.target.attr.value == self.delegate_field
                                        ):
                                            # Extract delegate class from assignment
                                            if isinstance(item.value, cst.Call):
                                                if isinstance(item.value.func, cst.Name):
                                                    self.delegate_type = item.value.func.value
        return True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and update to inherit from delegate."""
        if original_node.name.value != self.class_name:
            return updated_node

        if not self.delegate_type:
            return updated_node

        # Add inheritance from delegate type
        new_bases = list(updated_node.bases) + [cst.Arg(value=cst.Name(self.delegate_type))]

        # Update __init__ method and remove delegation methods
        new_body_stmts: list[cst.BaseStatement] = []
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                # Transform __init__ method
                if stmt.name.value == "__init__":
                    stmt = self._transform_init_method(stmt)
                # Remove delegation methods (get_X, set_X that delegate to _person)
                elif self._is_delegation_method(stmt):
                    continue
            new_body_stmts.append(stmt)  # type: ignore[arg-type]

        return updated_node.with_changes(
            bases=new_bases, body=updated_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _is_delegation_method(self, method: cst.FunctionDef) -> bool:
        """Check if a method is a delegation method that delegates to the delegate field.

        Args:
            method: The method to check

        Returns:
            True if the method delegates to the delegate field
        """
        # Check if the method body only contains delegation calls/accesses
        if isinstance(method.body, cst.IndentedBlock):
            for stmt in method.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for item in stmt.body:
                        if isinstance(item, cst.Return):
                            if self._is_delegated_return(item.value):
                                return True
                        elif isinstance(item, cst.Assign):
                            if self._is_delegated_assignment(item):
                                return True
        return False

    def _is_delegated_return(self, return_val: cst.BaseExpression | None) -> bool:
        """Check if a return value delegates to the delegate field.

        Args:
            return_val: The return value expression

        Returns:
            True if the return value is a delegation to self._field
        """
        if return_val is None:
            return False

        # Pattern: return self._field.attr
        if isinstance(return_val, cst.Attribute):
            return self._is_delegate_attribute(return_val.value)

        # Pattern: return self._field.method()
        if isinstance(return_val, cst.Call):
            if isinstance(return_val.func, cst.Attribute):
                return self._is_delegate_attribute(return_val.func.value)

        return False

    def _is_delegated_assignment(self, assignment: cst.Assign) -> bool:
        """Check if an assignment delegates to the delegate field.

        Args:
            assignment: The assignment statement

        Returns:
            True if the assignment delegates to self._field
        """
        if not isinstance(assignment.value, cst.BaseExpression):
            return False

        for target in assignment.targets:
            if isinstance(target.target, cst.Attribute):
                if self._is_delegate_attribute(target.target.value):
                    return True

        return False

    def _is_delegate_attribute(self, node: cst.BaseExpression) -> bool:
        """Check if an expression is an access to the delegate field (self._field).

        Args:
            node: The expression to check

        Returns:
            True if the expression is self._field
        """
        return (
            isinstance(node, cst.Attribute)
            and isinstance(node.value, cst.Name)
            and node.value.value == "self"
            and node.attr.value == self.delegate_field
        )

    def _transform_init_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform the __init__ method to call super().__init__().

        Args:
            node: The __init__ method to transform

        Returns:
            The transformed __init__ method
        """
        # Create super().__init__() call with all parameters except self
        call_args = []
        for param in node.params.params:
            if param.name.value != "self":
                call_args.append(cst.Arg(value=cst.Name(param.name.value)))

        super_call = cst.Expr(
            value=cst.Call(
                func=cst.Attribute(
                    value=cst.Call(func=cst.Name("super")), attr=cst.Name("__init__")
                ),
                args=call_args,
            )
        )

        super_call_stmt = cst.SimpleStatementLine(body=[super_call])

        # Create new body with only the super call
        new_body = cst.IndentedBlock(body=[super_call_stmt])

        return node.with_changes(body=new_body)


# Register the command
register_command(ReplaceDelegationWithInheritanceCommand)
