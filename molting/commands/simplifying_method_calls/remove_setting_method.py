"""Remove Setting Method refactoring command."""


import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class RemoveSettingMethodCommand(BaseCommand):
    """Command to remove a setter method to make a field immutable."""

    name = "remove-setting-method"

    def _derive_setter_name(self, field_name: str) -> str:
        """Derive the setter method name from a field name.

        Args:
            field_name: The field name (e.g., '_id', 'name')

        Returns:
            The setter method name (e.g., 'set_id', 'set_name')
        """
        clean_field_name = field_name.lstrip("_")
        return f"set_{clean_field_name}"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-setting-method refactoring using libCST.

        Raises:
            ValueError: If class or field not found
        """
        target = self.params["target"]
        class_name, field_name = parse_target(target, expected_parts=2)
        setter_name = self._derive_setter_name(field_name)

        # Apply the transformation
        self.apply_libcst_transform(RemoveSettingMethodTransformer, class_name, setter_name)


class RemoveSettingMethodTransformer(cst.CSTTransformer):
    """Transforms a class to remove a setter method and update call sites."""

    def __init__(self, class_name: str, setter_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the setter method
            setter_name: Name of the setter method to remove
        """
        self.class_name = class_name
        self.setter_name = setter_name
        self.in_target_class = False
        # Track var_name -> setter_value for variables assigned from class constructor
        self.var_to_setter_value: dict[str, cst.BaseExpression] = {}
        # Track which variables are assigned from our target class
        self.vars_from_target_class: set[str] = set()
        # Statements to remove (setter calls)
        self.stmts_to_remove: set[int] = set()

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and remove the setter method if found."""
        if original_node.name.value == self.class_name:
            self.in_target_class = False

            # Filter out the setter method from the class body
            if isinstance(updated_node.body, cst.IndentedBlock):
                new_body = []
                setter_found = False

                for stmt in updated_node.body.body:
                    if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.setter_name:
                        setter_found = True
                        continue  # Skip this method
                    new_body.append(stmt)

                if not setter_found:
                    raise ValueError(
                        f"Setter method '{self.setter_name}' not found "
                        f"in class '{self.class_name}'"
                    )

                # Return the class with updated body
                return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

        return updated_node

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> bool:  # noqa: N802
        """Visit simple statements to find variable assignments and setter calls."""
        for stmt in node.body:
            # Check for assignment: var = ClassName(...)
            if isinstance(stmt, cst.Assign):
                for target in stmt.targets:
                    if isinstance(target.target, cst.Name):
                        var_name = target.target.value
                        # Check if RHS is a call to our target class
                        if isinstance(stmt.value, cst.Call):
                            if isinstance(stmt.value.func, cst.Name):
                                if stmt.value.func.value == self.class_name:
                                    self.vars_from_target_class.add(var_name)

            # Check for setter call: var.set_field(value)
            if isinstance(stmt, cst.Expr):
                call = stmt.value
                if isinstance(call, cst.Call):
                    if isinstance(call.func, cst.Attribute):
                        attr = call.func
                        if isinstance(attr.value, cst.Name) and attr.attr.value == self.setter_name:
                            var_name = attr.value.value
                            if var_name in self.vars_from_target_class and call.args:
                                # Store the setter value for this variable
                                self.var_to_setter_value[var_name] = call.args[0].value
        return True

    def leave_SimpleStatementLine(  # noqa: N802
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        """Remove setter call statements."""
        for stmt in original_node.body:
            if isinstance(stmt, cst.Expr):
                call = stmt.value
                if isinstance(call, cst.Call):
                    if isinstance(call.func, cst.Attribute):
                        attr = call.func
                        if (
                            isinstance(attr.value, cst.Name)
                            and attr.attr.value == self.setter_name
                            and attr.value.value in self.vars_from_target_class
                        ):
                            # Remove this setter call statement
                            return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Update constructor calls to include the setter value."""
        # Check if this is a call to our target class constructor
        if isinstance(updated_node.func, cst.Name):
            if updated_node.func.value == self.class_name:
                # Find what variable this call is assigned to
                # We need to check if this constructor's result has a setter value
                # This is tricky - we need to find the variable name
                # For now, we'll update constructors that have None as first arg
                if updated_node.args:
                    first_arg = updated_node.args[0]
                    if isinstance(first_arg.value, cst.Name):
                        if first_arg.value.value == "None":
                            # This is a candidate for update
                            # Find the matching setter value
                            # We need context to know which variable
                            pass
        return updated_node

    def leave_Assign(  # noqa: N802
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> cst.Assign:
        """Update constructor calls in assignments."""
        for target in original_node.targets:
            if isinstance(target.target, cst.Name):
                var_name = target.target.value
                if var_name in self.var_to_setter_value:
                    # Check if RHS is a call to our target class
                    if isinstance(updated_node.value, cst.Call):
                        call = updated_node.value
                        if isinstance(call.func, cst.Name):
                            if call.func.value == self.class_name:
                                # Replace the first argument with setter value
                                setter_value = self.var_to_setter_value[var_name]
                                new_args = [cst.Arg(value=setter_value)]
                                new_args.extend(call.args[1:])
                                new_call = call.with_changes(args=new_args)
                                return updated_node.with_changes(value=new_call)
        return updated_node


# Register the command
register_command(RemoveSettingMethodCommand)
