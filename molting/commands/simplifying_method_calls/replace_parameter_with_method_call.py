"""Replace Parameter with Method Call refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class ReplaceParameterWithMethodCallCommand(BaseCommand):
    """Replace a method parameter with a direct method call.

    This refactoring removes a method parameter and replaces all references to that
    parameter with calls to a getter method. Instead of passing a value as a
    parameter, the method obtains the value by calling another method on the same
    object (typically self.get_*).

    **When to use:**
    - A method parameter is derived from a call to another method on the same object
    - The parameter adds unnecessary coupling and complexity to the method signature
    - You want to simplify the interface by removing the parameter dependency
    - The getter method is always available and returns the needed value

    **Example:**
    Before:
        class Employee:
            def __init__(self, salary):
                self.salary = salary

            def get_salary(self):
                return self.salary

            def calculate_bonus(self, salary):
                return salary * 0.1

        emp = Employee(50000)
        bonus = emp.calculate_bonus(emp.get_salary())

    After:
        class Employee:
            def __init__(self, salary):
                self.salary = salary

            def get_salary(self):
                return self.salary

            def calculate_bonus(self):
                return self.get_salary() * 0.1

        emp = Employee(50000)
        bonus = emp.calculate_bonus()
    """

    name = "replace-parameter-with-method-call"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-parameter-with-method-call refactoring using libCST.

        Raises:
            ValueError: If method or parameter not found or target format is invalid
        """
        target = self.params["target"]
        class_name, method_name, param_name = parse_target(target, expected_parts=3)

        # Derive the method name from the parameter name
        # e.g., discount_level -> get_discount_level
        getter_method_name = f"get_{param_name}"

        # Apply the transformation
        self.apply_libcst_transform(
            ReplaceParameterWithMethodCallTransformer,
            class_name,
            method_name,
            param_name,
            getter_method_name,
        )


class ReplaceParameterWithMethodCallTransformer(cst.CSTTransformer):
    """Transforms a class to replace a parameter with a method call."""

    def __init__(
        self, class_name: str, method_name: str, param_name: str, getter_method_name: str
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method with the parameter
            param_name: Name of the parameter to replace
            getter_method_name: Name of the getter method to call instead
        """
        self.class_name = class_name
        self.method_name = method_name
        self.param_name = param_name
        self.getter_method_name = getter_method_name
        self.in_target_class = False
        self.in_target_method = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition."""
        if original_node.name.value == self.class_name:
            self.in_target_class = False
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to track if we're in the target method."""
        if self.in_target_class and node.name.value == self.method_name:
            self.in_target_method = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and remove the parameter if it's the target method."""
        if self.in_target_class and original_node.name.value == self.method_name:
            self.in_target_method = False
            # Remove the parameter from the method signature
            # Use original_node.params to avoid already-transformed params
            new_params = []
            for param in original_node.params.params:
                if param.name.value != self.param_name:
                    new_params.append(param)
            return updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_params)
            )
        return updated_node

    def leave_Name(  # noqa: N802
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        """Leave name node and replace parameter usage with method call."""
        if self.in_target_method and updated_node.value == self.param_name:
            return self._create_getter_method_call()
        return updated_node

    def leave_SimpleStatementLine(  # noqa: N802
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        """Remove assignment statements that assign the parameter value."""
        if not self.in_target_class or self.in_target_method:
            return updated_node

        if self._should_remove_assignment(updated_node):
            return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Leave call expression and remove the argument at call sites."""
        if (
            self.in_target_class
            and not self.in_target_method
            and self._is_target_method_call(updated_node)
        ):
            # Remove the argument corresponding to the parameter
            new_args = []
            for arg in updated_node.args:
                if not self._is_argument_for_param(arg):
                    new_args.append(arg)
            return updated_node.with_changes(args=new_args)
        return updated_node

    def _should_remove_assignment(self, statement_line: cst.SimpleStatementLine) -> bool:
        """Check if an assignment statement should be removed.

        Args:
            statement_line: The statement line to check

        Returns:
            True if this is an assignment to the parameter with getter call value
        """
        if len(statement_line.body) != 1:
            return False

        stmt = statement_line.body[0]
        if not isinstance(stmt, cst.Assign):
            return False

        if len(stmt.targets) != 1:
            return False

        target = stmt.targets[0].target
        if not isinstance(target, cst.Name) or target.value != self.param_name:
            return False

        return self._is_getter_call(stmt.value)

    def _create_getter_method_call(self) -> cst.Call:
        """Create a call expression for self.get_<param>().

        Returns:
            A Call node representing self.get_<param>()
        """
        return cst.Call(
            func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.getter_method_name))
        )

    def _is_target_method_call(self, node: cst.Call) -> bool:
        """Check if a call node is a call to self.method_name().

        Args:
            node: The call node to check

        Returns:
            True if this is a call to the target method, False otherwise
        """
        if not isinstance(node.func, cst.Attribute):
            return False

        return (
            isinstance(node.func.value, cst.Name)
            and node.func.value.value == "self"
            and node.func.attr.value == self.method_name
        )

    def _is_getter_call(self, value: cst.BaseExpression) -> bool:
        """Check if a value is a call to self.get_<param>().

        Args:
            value: The expression to check

        Returns:
            True if this is a call to the getter method, False otherwise
        """
        if not isinstance(value, cst.Call):
            return False
        if not isinstance(value.func, cst.Attribute):
            return False
        return (
            isinstance(value.func.value, cst.Name)
            and value.func.value.value == "self"
            and value.func.attr.value == self.getter_method_name
        )

    def _is_argument_for_param(self, arg: cst.Arg) -> bool:
        """Check if this argument is the one we want to remove.

        Args:
            arg: The argument to check

        Returns:
            True if this is the argument for the parameter we're removing
        """
        if isinstance(arg.value, cst.Name) and arg.value.value == self.param_name:
            return True
        if self._is_getter_call(arg.value):
            return True
        return False


# Register the command
register_command(ReplaceParameterWithMethodCallCommand)
