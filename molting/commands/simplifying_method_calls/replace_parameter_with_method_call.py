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

        # First, analyze the code to find the getter method name
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Find what method is called at call sites for this parameter
        analyzer = CallSiteAnalyzer(class_name, method_name, param_name)
        module.visit(analyzer)

        getter_method_name = analyzer.getter_method_name
        if not getter_method_name:
            # Fall back to simple derivation if we can't find it
            getter_method_name = f"get_{param_name}"

        # Apply the transformation
        self.apply_libcst_transform(
            ReplaceParameterWithMethodCallTransformer,
            class_name,
            method_name,
            param_name,
            getter_method_name,
        )


class CallSiteAnalyzer(cst.CSTVisitor):
    """Analyzes call sites to determine the getter method name."""

    def __init__(self, class_name: str, method_name: str, param_name: str) -> None:
        """Initialize the analyzer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method with the parameter
            param_name: Name of the parameter to analyze
        """
        self.class_name = class_name
        self.method_name = method_name
        self.param_name = param_name
        self.getter_method_name: str | None = None
        self.in_target_class = False
        self.param_position: int | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Leave class definition."""
        if node.name.value == self.class_name:
            self.in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to find the parameter position."""
        if self.in_target_class and node.name.value == self.method_name:
            # Find the position of the parameter
            for i, param in enumerate(node.params.params):
                if param.name.value == self.param_name:
                    # Subtract 1 to account for 'self'
                    self.param_position = i - 1 if i > 0 else 0
                    break
        return True

    def visit_Call(self, node: cst.Call) -> bool:  # noqa: N802
        """Visit call to find calls to the target method."""
        if not self.in_target_class or self.param_position is None:
            return True

        # Check if this is a call to self.method_name
        if not isinstance(node.func, cst.Attribute):
            return True

        if not (
            isinstance(node.func.value, cst.Name)
            and node.func.value.value == "self"
            and node.func.attr.value == self.method_name
        ):
            return True

        # This is a call to self.method_name - get the argument at param_position
        if self.param_position < len(node.args):
            arg = node.args[self.param_position]

            # Check if the argument is a call to a getter method
            if isinstance(arg.value, cst.Call) and isinstance(arg.value.func, cst.Attribute):
                if (
                    isinstance(arg.value.func.value, cst.Name)
                    and arg.value.func.value.value == "self"
                ):
                    # This is a call to self.something()
                    self.getter_method_name = arg.value.func.attr.value
                    return False  # Stop searching

            # Check if the argument is a variable
            if isinstance(arg.value, cst.Name):
                var_name = arg.value.value
                # Try to infer the getter method name from the variable name
                self.getter_method_name = f"get_{var_name}"
                return False  # Stop searching

        return True


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
        self.param_position: int | None = None

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
            # Find the position of the parameter
            for i, param in enumerate(node.params.params):
                if param.name.value == self.param_name:
                    # Subtract 1 to account for 'self'
                    self.param_position = i - 1 if i > 0 else 0
                    break

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and remove the parameter if it's the target method."""
        if self.in_target_class and original_node.name.value == self.method_name:
            self.in_target_method = False
            # Remove the parameter from the method signature
            new_params = []
            for param in original_node.params.params:
                if param.name.value != self.param_name:
                    new_params.append(param)

            # Insert a local variable assignment at the start of the method body
            assignment = self._create_local_variable_assignment()

            # Insert the assignment as the first statement in the body
            new_body = updated_node.body
            if isinstance(new_body, cst.IndentedBlock):
                new_statements = [assignment] + list(new_body.body)
                new_body = new_body.with_changes(body=new_statements)

            return updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_params), body=new_body
            )
        return updated_node

    def leave_SimpleStatementLine(  # noqa: N802
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        """Remove assignment statements that assign the parameter value."""
        # Don't remove assignments for now - this feature needs more work
        # to correctly identify which assignments should be removed
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Leave call expression and remove the argument at call sites."""
        if (
            self.in_target_class
            and not self.in_target_method
            and self._is_target_method_call(updated_node)
            and self.param_position is not None
        ):
            # Remove the argument at the parameter position
            new_args = []
            for i, arg in enumerate(updated_node.args):
                if i != self.param_position:
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
        if not isinstance(target, cst.Name):
            return False

        # Check if the variable name relates to the parameter
        var_name = target.value
        if not self._could_be_variable_for_param(var_name):
            return False

        return self._is_getter_call(stmt.value)

    def _could_be_variable_for_param(self, var_name: str) -> bool:
        """Check if a variable name could be for our parameter."""
        # Check if variable name contains the parameter name
        return self.param_name in var_name or var_name in self.param_name

    def _create_local_variable_assignment(self) -> cst.SimpleStatementLine:
        """Create a local variable assignment for the parameter.

        Returns:
            A SimpleStatementLine representing: param_name = self.getter_method_name()
        """
        return cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.param_name))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("self"), attr=cst.Name(self.getter_method_name)
                        )
                    ),
                )
            ]
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
        """Check if a value is a call to a getter method.

        Args:
            value: The expression to check

        Returns:
            True if this is a call to a getter method, False otherwise
        """
        if not isinstance(value, cst.Call):
            return False
        if not isinstance(value.func, cst.Attribute):
            return False
        if not isinstance(value.func.value, cst.Name):
            return False
        if value.func.value.value != "self":
            return False
        # Check if the method name is a getter
        return value.func.attr.value.startswith("get_")


# Register the command
register_command(ReplaceParameterWithMethodCallCommand)
