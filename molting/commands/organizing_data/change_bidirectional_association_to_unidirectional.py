"""Change Bidirectional Association to Unidirectional refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class ChangeBidirectionalAssociationToUnidirectionalCommand(BaseCommand):
    """Remove unnecessary bidirectional associations to simplify class relationships.

    This refactoring converts a bidirectional association (two-way dependency) into a
    unidirectional one (one-way dependency) when one class no longer needs to access
    features from the other. It removes the back pointer field, its accessor methods,
    and all related initialization and management code from the target class while
    updating the source class to remove references to these now-unused methods.

    **When to use:**
    - A bidirectional association is more complex than necessary for the current design
    - One end of the association is never actually used in your code
    - You want to reduce coupling and simplify the object model
    - A unidirectional reference is sufficient for your navigation needs
    - You're refactoring to eliminate unnecessary dependencies between classes

    **Example:**
    Before:
        # Two-way relationship: Customer knows about Orders, Orders know about Customer
        class Customer:
            def __init__(self):
                self._orders = []

            def add_order(self, order):
                self._orders.append(order)

            def remove_order(self, order):
                self._orders.remove(order)

        class Order:
            def __init__(self, customer):
                self._customer = customer
                customer.add_order(self)

            def set_customer(self, customer):
                if self._customer:
                    self._customer.remove_order(self)
                self._customer = customer
                customer.add_order(self)

    After:
        # One-way relationship: only Customer knows about Orders
        class Customer:
            def __init__(self):
                self._orders = []

            def add_order(self, order):
                self._orders.append(order)

            def remove_order(self, order):
                self._orders.remove(order)

        class Order:
            def __init__(self, customer):
                pass  # No back reference to customer
    """

    name = "change-bidirectional-association-to-unidirectional"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for "
                "change-bidirectional-association-to-unidirectional: 'target'"
            )

    def execute(self) -> None:
        """Apply change-bidirectional-association-to-unidirectional refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ChangeBidirectionalAssociationToUnidirectionalTransformer(
            class_name, field_name
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ChangeBidirectionalAssociationToUnidirectionalTransformer(cst.CSTTransformer):
    """Transform bidirectional association to unidirectional by removing back pointers."""

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the field to remove
            field_name: Name of the field to remove (the back pointer)
        """
        self.class_name = class_name
        self.field_name = field_name

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Remove back pointer from target class and clean references in other classes."""
        if updated_node.name.value == self.class_name:
            # This is the class with the back pointer - remove it
            return self._remove_back_pointer_from_class(updated_node)
        else:
            # This is another class - clean up references to the back pointer
            return self._clean_back_pointer_references(updated_node)

    def _remove_back_pointer_from_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Remove the back pointer field and its methods.

        Args:
            class_def: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                # Skip methods that manage the back pointer
                if self._is_back_pointer_method(stmt):
                    continue
                # Transform __init__ to remove field initialization
                if stmt.name.value == "__init__":
                    transformed = self._transform_init_method(stmt)
                    # Only add if __init__ is not empty (has more than just pass)
                    if transformed:
                        new_body.append(transformed)
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # If body is empty, add pass statement
        if not new_body:
            new_body = [cst.SimpleStatementLine(body=[cst.Pass()])]

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _is_back_pointer_method(self, func_def: cst.FunctionDef) -> bool:
        """Check if a method is only for managing the back pointer.

        Args:
            func_def: Function definition to check

        Returns:
            True if this method manages the back pointer collection
        """
        method_name = func_def.name.value
        # The field name is _orders, so we look for add_order and remove_order
        singular = self.field_name.lstrip("_").rstrip("s")
        if method_name == f"add_{singular}":
            return True
        if method_name == f"remove_{singular}":
            return True
        return False

    def _transform_init_method(self, init_method: cst.FunctionDef) -> cst.FunctionDef | None:
        """Remove field initialization from __init__.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method with field initialization removed, or None if empty
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                new_stmt_body: list[cst.BaseSmallStatement] = []
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        # Check if this assigns to self._field_name
                        should_remove = False
                        for target in body_item.targets:
                            if self._is_field_assignment(target):
                                should_remove = True
                                break
                        if not should_remove:
                            new_stmt_body.append(body_item)
                    else:
                        new_stmt_body.append(body_item)

                # Only add the statement line if it has content
                if new_stmt_body:
                    new_body.append(stmt.with_changes(body=new_stmt_body))
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # If __init__ is now empty, return None to indicate it should be removed
        if not new_body:
            return None

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _is_field_assignment(self, target: cst.AssignTarget) -> bool:
        """Check if an assignment target is assigning to the target field.

        Args:
            target: The assignment target to check

        Returns:
            True if this is an assignment to self.field_name
        """
        if not isinstance(target.target, cst.Attribute):
            return False
        if not isinstance(target.target.value, cst.Name):
            return False
        return target.target.value.value == "self" and target.target.attr.value == self.field_name

    def _clean_back_pointer_references(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Remove calls to back pointer methods from other classes.

        Args:
            class_def: The class definition to clean

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                # Check if this is a setter that should be removed
                if self._is_setter_to_remove(stmt):
                    continue
                # Clean the method
                cleaned = self._clean_method(stmt)
                if cleaned:
                    new_body.append(cleaned)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _is_setter_to_remove(self, func_def: cst.FunctionDef) -> bool:
        """Check if this is a setter method that should be removed.

        Args:
            func_def: Function definition to check

        Returns:
            True if this setter manages the bidirectional link
        """
        # Check if this is a set_* method
        if not func_def.name.value.startswith("set_"):
            return False

        # Check if it contains calls to add_ or remove_ methods that match our back pointer
        singular = self.field_name.lstrip("_").rstrip("s")
        for stmt in func_def.body.body:
            if self._contains_back_pointer_call(stmt, singular):
                return True
        return False

    def _contains_back_pointer_call(self, node: cst.CSTNode, singular: str) -> bool:
        """Check if a node contains calls to back pointer methods.

        Args:
            node: The node to check
            singular: The singular form of the back pointer field

        Returns:
            True if the node contains calls to add_/remove_ methods
        """
        if isinstance(node, cst.SimpleStatementLine):
            for item in node.body:
                if isinstance(item, cst.Expr) and isinstance(item.value, cst.Call):
                    if isinstance(item.value.func, cst.Attribute):
                        method_name = item.value.func.attr.value
                        if method_name in [f"add_{singular}", f"remove_{singular}"]:
                            return True
        elif isinstance(node, cst.If):
            # Check the if body
            for stmt in node.body.body:
                if self._contains_back_pointer_call(stmt, singular):
                    return True
            # Check the orelse (else/elif)
            if node.orelse:
                if isinstance(node.orelse, cst.If):
                    if self._contains_back_pointer_call(node.orelse, singular):
                        return True
                elif isinstance(node.orelse, cst.Else):
                    for stmt in node.orelse.body.body:
                        if self._contains_back_pointer_call(stmt, singular):
                            return True
        return False

    def _clean_method(self, method: cst.FunctionDef) -> cst.FunctionDef | None:
        """Remove back pointer management from a method.

        Args:
            method: The method to clean

        Returns:
            Modified method or None if it should be removed
        """
        # For __init__, we need to simplify it
        if method.name.value == "__init__":
            return self._clean_init_method(method)

        return method

    def _clean_init_method(self, init_method: cst.FunctionDef) -> cst.FunctionDef | None:
        """Remove back pointer calls from __init__.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method or None if empty
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                new_stmt_body: list[cst.BaseSmallStatement] = []
                for body_item in stmt.body:
                    # Remove calls to setters that manage the bidirectional link
                    if isinstance(body_item, cst.Expr) and isinstance(body_item.value, cst.Call):
                        if isinstance(body_item.value.func, cst.Attribute):
                            if body_item.value.func.attr.value.startswith("set_"):
                                # Replace set_customer(customer) with self.customer = customer
                                # Get the parameter name
                                param_name = body_item.value.func.attr.value[4:]  # Remove "set_"
                                if len(body_item.value.args) == 1:
                                    arg = body_item.value.args[0]
                                    if isinstance(arg, cst.Arg) and isinstance(arg.value, cst.Name):
                                        # Create direct assignment
                                        new_stmt_body.append(
                                            cst.Assign(
                                                targets=[
                                                    cst.AssignTarget(
                                                        target=cst.Attribute(
                                                            value=cst.Name("self"),
                                                            attr=cst.Name(param_name),
                                                        )
                                                    )
                                                ],
                                                value=arg.value,
                                            )
                                        )
                                        continue
                    # Keep assignments that don't involve the setter
                    if isinstance(body_item, cst.Assign):
                        # Check if it's setting to None or similar - we can skip these
                        # if there's a corresponding setter call
                        should_keep = True
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Attribute):
                                if isinstance(target.target.value, cst.Name):
                                    if target.target.value.value == "self":
                                        # Check if field is set to None with setter call
                                        if isinstance(body_item.value, cst.Name):
                                            if body_item.value.value == "None":
                                                # Check if there's a setter call in this __init__
                                                if self._has_setter_call_for_field(
                                                    init_method, target.target.attr.value
                                                ):
                                                    should_keep = False
                                                    break
                        if should_keep:
                            new_stmt_body.append(body_item)
                    else:
                        new_stmt_body.append(body_item)

                if new_stmt_body:
                    new_body.append(stmt.with_changes(body=new_stmt_body))
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        if not new_body:
            return None

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _has_setter_call_for_field(self, method: cst.FunctionDef, field_name: str) -> bool:
        """Check if a method contains a setter call for a field.

        Args:
            method: The method to check
            field_name: The field name to look for

        Returns:
            True if there's a setter call for this field
        """
        setter_name = f"set_{field_name.lstrip('_')}"
        for stmt in method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.Expr) and isinstance(item.value, cst.Call):
                        if isinstance(item.value.func, cst.Attribute):
                            if item.value.func.attr.value == setter_name:
                                return True
        return False


# Register the command
register_command(ChangeBidirectionalAssociationToUnidirectionalCommand)
