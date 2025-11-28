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
        # Scoped per function to avoid conflicts
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

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform function body to update constructor calls and remove setters."""
        if not isinstance(updated_node.body, cst.IndentedBlock):
            return updated_node

        # First pass: collect var->setter_value mappings and identify variables from target class
        var_to_setter_value: dict[str, cst.BaseExpression] = {}
        vars_from_target_class: set[str] = set()

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for inner_stmt in stmt.body:
                    # Check for assignment: var = ClassName(...)
                    if isinstance(inner_stmt, cst.Assign):
                        for target in inner_stmt.targets:
                            if isinstance(target.target, cst.Name):
                                var_name = target.target.value
                                if isinstance(inner_stmt.value, cst.Call):
                                    if isinstance(inner_stmt.value.func, cst.Name):
                                        if inner_stmt.value.func.value == self.class_name:
                                            vars_from_target_class.add(var_name)

                    # Check for setter call: var.set_field(value)
                    if isinstance(inner_stmt, cst.Expr):
                        call = inner_stmt.value
                        if isinstance(call, cst.Call):
                            if isinstance(call.func, cst.Attribute):
                                attr = call.func
                                if (
                                    isinstance(attr.value, cst.Name)
                                    and attr.attr.value == self.setter_name
                                ):
                                    var_name = attr.value.value
                                    if var_name in vars_from_target_class and call.args:
                                        var_to_setter_value[var_name] = call.args[0].value

        # Second pass: transform statements
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this is a setter call to remove
                should_remove = False
                for inner_stmt in stmt.body:
                    if isinstance(inner_stmt, cst.Expr):
                        call = inner_stmt.value
                        if isinstance(call, cst.Call):
                            if isinstance(call.func, cst.Attribute):
                                attr = call.func
                                if (
                                    isinstance(attr.value, cst.Name)
                                    and attr.attr.value == self.setter_name
                                    and attr.value.value in vars_from_target_class
                                ):
                                    should_remove = True
                                    break

                if should_remove:
                    continue  # Skip this statement

                # Check if this is a constructor assignment to update
                for inner_stmt in stmt.body:
                    if isinstance(inner_stmt, cst.Assign):
                        for target in inner_stmt.targets:
                            if isinstance(target.target, cst.Name):
                                var_name = target.target.value
                                if var_name in var_to_setter_value:
                                    if isinstance(inner_stmt.value, cst.Call):
                                        call = inner_stmt.value
                                        if isinstance(call.func, cst.Name):
                                            if call.func.value == self.class_name:
                                                # Update the constructor call
                                                setter_value = var_to_setter_value[var_name]
                                                new_args = [cst.Arg(value=setter_value)]
                                                new_args.extend(call.args[1:])
                                                new_call = call.with_changes(args=new_args)
                                                new_assign = inner_stmt.with_changes(value=new_call)
                                                new_stmt = stmt.with_changes(body=[new_assign])
                                                new_body.append(new_stmt)
                                                break
                        else:
                            continue
                        break
                else:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))


# Register the command
register_command(RemoveSettingMethodCommand)
