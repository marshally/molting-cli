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

        # Read source and find the parameter index and actual getter method
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Two-pass discovery:
        # Pass 1: find parameter index
        finder = _ParameterInfoFinder(class_name, method_name, param_name)
        module.visit(finder)

        if finder.param_index is None:
            raise ValueError(f"Parameter '{param_name}' not found in {class_name}::{method_name}")

        # Pass 2: find getter method name from call sites (now that we have param_index)
        getter_finder = _GetterFinder(method_name, finder.param_index, finder.getter_assignments)
        module.visit(getter_finder)

        # Use discovered getter or fall back to convention
        getter_method_name = getter_finder.getter_method_name or f"get_{param_name}"

        # Apply the transformation
        self.apply_libcst_transform(
            ReplaceParameterWithMethodCallTransformer,
            class_name,
            method_name,
            param_name,
            getter_method_name,
            finder.param_index,
        )


class ReplaceParameterWithMethodCallTransformer(cst.CSTTransformer):
    """Transforms a class to replace a parameter with a method call."""

    def __init__(
        self,
        class_name: str,
        method_name: str,
        param_name: str,
        getter_method_name: str,
        param_index: int,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method with the parameter
            param_name: Name of the parameter to replace
            getter_method_name: Name of the getter method to call instead
            param_index: Index of the parameter in the method signature (0-based, excluding self)
        """
        self.class_name = class_name
        self.method_name = method_name
        self.param_name = param_name
        self.getter_method_name = getter_method_name
        self.param_index = param_index
        self.in_target_class = False
        self.in_target_method = False
        self.param_is_used_elsewhere = False

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
            # Always inline - don't add assignment, just replace usages with getter calls
            self.param_is_used_elsewhere = False

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

            # Clean up trailing comma on last param if present
            if new_params:
                last_param = new_params[-1]
                if last_param.comma != cst.MaybeSentinel.DEFAULT:
                    new_params[-1] = last_param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

            # If the parameter is used elsewhere in the method, add an assignment
            # after the docstring (if any) to replace the parameter value
            if self.param_is_used_elsewhere:
                assignment = self._create_parameter_assignment()
                body_stmts = list(updated_node.body.body)

                # Find insertion point: after docstring if present
                insert_idx = 0
                first_stmt = body_stmts[0] if body_stmts else None
                if first_stmt is not None and isinstance(first_stmt, cst.SimpleStatementLine):
                    if self._is_docstring(first_stmt):
                        insert_idx = 1

                body_stmts.insert(insert_idx, assignment)
                new_body = updated_node.body.with_changes(body=body_stmts)
            else:
                new_body = updated_node.body

            # Reset param_is_used_elsewhere after processing the target method
            self.param_is_used_elsewhere = False

            return updated_node.with_changes(
                params=updated_node.params.with_changes(params=new_params), body=new_body
            )
        return updated_node

    def _is_docstring(self, stmt: cst.SimpleStatementLine) -> bool:
        """Check if a statement is a docstring."""
        if len(stmt.body) != 1:
            return False
        expr = stmt.body[0]
        if not isinstance(expr, cst.Expr):
            return False
        return isinstance(expr.value, (cst.SimpleString, cst.ConcatenatedString))

    def leave_Name(  # noqa: N802
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        """Leave name node and replace parameter usage with method call."""
        # Replace all usages of the parameter with the getter method call
        if self.in_target_method and updated_node.value == self.param_name:
            return self._create_getter_method_call()
        return updated_node

    def leave_SimpleStatementLine(  # noqa: N802
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        """Remove assignment statements that assign the parameter value."""
        if self.in_target_method:
            return updated_node

        if self._should_remove_assignment(updated_node):
            return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Leave call expression and remove the argument at call sites."""
        # Remove arguments from all call sites, but only if we're not inside the target method
        if not self.in_target_method and self._is_target_method_call(updated_node):
            # Remove the argument at the parameter index (by position)
            new_args = []
            for i, arg in enumerate(updated_node.args):
                if i != self.param_index:
                    new_args.append(arg)

            # Clean up trailing comma on last argument if present
            if new_args:
                last_arg = new_args[-1]
                if last_arg.comma != cst.MaybeSentinel.DEFAULT:
                    new_args[-1] = last_arg.with_changes(comma=cst.MaybeSentinel.DEFAULT)

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

        return self._is_any_getter_call(stmt.value)

    def _create_getter_method_call(self) -> cst.Call:
        """Create a call expression for self.get_<param>().

        Returns:
            A Call node representing self.get_<param>()
        """
        return cst.Call(
            func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.getter_method_name))
        )

    def _create_parameter_assignment(self) -> cst.SimpleStatementLine:
        """Create an assignment statement for the parameter inside the method.

        Creates: <param_name> = self.get_<param_name>()

        Returns:
            A SimpleStatementLine with the assignment
        """
        assignment = cst.Assign(
            targets=[cst.AssignTarget(target=cst.Name(self.param_name))],
            value=self._create_getter_method_call(),
        )
        return cst.SimpleStatementLine(body=[assignment])

    def _is_target_method_call(self, node: cst.Call) -> bool:
        """Check if a call node is a call to <receiver>.method_name().

        This matches any call to the target method, whether it's self.method_name()
        or order.method_name() or any other receiver.

        Args:
            node: The call node to check

        Returns:
            True if this is a call to the target method, False otherwise
        """
        if not isinstance(node.func, cst.Attribute):
            return False

        # Match any call to method_name, regardless of the receiver
        return node.func.attr.value == self.method_name

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

    def _is_any_getter_call(self, value: cst.BaseExpression) -> bool:
        """Check if a value is a call to <receiver>.get_<param>().

        This matches any call to the getter method, whether it's self.get_discount_level()
        or order.get_discount_level() or any other receiver.

        Args:
            value: The expression to check

        Returns:
            True if this is a call to the getter method with any receiver, False otherwise
        """
        if not isinstance(value, cst.Call):
            return False
        if not isinstance(value.func, cst.Attribute):
            return False
        # Match any call to getter_method_name, regardless of the receiver
        return value.func.attr.value == self.getter_method_name

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

    def _is_param_used_elsewhere_in_method(self, method_node: cst.FunctionDef) -> bool:
        """Check if the parameter is used elsewhere besides as a call argument.

        Scans the method body to find usages of the parameter. Returns True if the
        parameter is referenced anywhere other than as an argument to the target
        method call. This helps determine whether we can safely remove the assignment.

        Args:
            method_node: The method function definition to analyze

        Returns:
            True if the parameter is used elsewhere in the method body
        """
        visitor = _ParameterUsageVisitor(self.param_name, self.method_name)
        method_node.body.visit(visitor)
        return visitor.is_used_elsewhere


class _ParameterUsageVisitor(cst.CSTVisitor):
    """Helper visitor to detect parameter usage outside of call arguments."""

    def __init__(self, param_name: str, method_name: str) -> None:
        """Initialize the visitor.

        Args:
            param_name: The parameter name to look for
            method_name: The method name for target calls
        """
        self.param_name = param_name
        self.method_name = method_name
        self.is_used_elsewhere = False
        self.in_target_call = False
        self.in_assignment_target = False

    def visit_Call(self, node: cst.Call) -> bool:  # noqa: N802
        """Visit a call node to check if this is the target method call."""
        # Check if this is a call to the target method
        if isinstance(node.func, cst.Attribute):
            if node.func.attr.value == self.method_name:
                self.in_target_call = True

        return True

    def leave_Call(self, original_node: cst.Call) -> None:  # noqa: N802
        """Leave a call node."""
        if isinstance(original_node.func, cst.Attribute):
            if original_node.func.attr.value == self.method_name:
                self.in_target_call = False

    def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802
        """Visit a name node and check if it's the parameter we're looking for."""
        # Only count as "used elsewhere" if it's on the right side of an assignment
        # (not in an assignment target) and not in a target method call argument
        if (
            node.value == self.param_name
            and not self.in_target_call
            and not self.in_assignment_target
        ):
            self.is_used_elsewhere = True
        return True


class _ParameterInfoFinder(cst.CSTVisitor):
    """Finds parameter index and tracks getter assignments."""

    def __init__(self, class_name: str, method_name: str, param_name: str) -> None:
        """Initialize the finder.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method with the parameter
            param_name: Name of the parameter to find
        """
        self.class_name = class_name
        self.method_name = method_name
        self.param_name = param_name
        self.param_index: int | None = None
        self.in_target_class = False
        # Track assignments like: var_name = <receiver>.get_something()
        self.getter_assignments: dict[str, str] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track when we enter the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track when we leave the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Find the parameter index in the target method."""
        if self.in_target_class and node.name.value == self.method_name:
            # Find index of param_name (excluding 'self')
            for i, param in enumerate(node.params.params):
                if param.name.value == "self":
                    continue
                if param.name.value == self.param_name:
                    # Index in call args (0-based, self not passed as arg)
                    self.param_index = i - 1 if node.params.params[0].name.value == "self" else i
                    break
        return True

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Track assignments from getter method calls."""
        # Pattern: var_name = <receiver>.get_something()
        if len(node.targets) != 1:
            return True

        target = node.targets[0].target
        if not isinstance(target, cst.Name):
            return True

        # Check if RHS is a method call
        if not isinstance(node.value, cst.Call):
            return True

        if not isinstance(node.value.func, cst.Attribute):
            return True

        method_name = node.value.func.attr.value
        if method_name.startswith("get_"):
            # Record: var_name -> getter_method_name
            self.getter_assignments[target.value] = method_name

        return True


class _GetterFinder(cst.CSTVisitor):
    """Finds the getter method name from call site arguments."""

    def __init__(
        self, method_name: str, param_index: int, getter_assignments: dict[str, str]
    ) -> None:
        """Initialize the finder.

        Args:
            method_name: Name of the target method being refactored
            param_index: Index of the parameter in call arguments
            getter_assignments: Map from variable names to getter method names
        """
        self.method_name = method_name
        self.param_index = param_index
        self.getter_assignments = getter_assignments
        self.getter_method_name: str | None = None

    def visit_Call(self, node: cst.Call) -> bool:  # noqa: N802
        """Look for calls to the target method to discover the getter being used."""
        if not isinstance(node.func, cst.Attribute):
            return True

        if node.func.attr.value != self.method_name:
            return True

        # Found a call to the target method - check argument at param_index
        if len(node.args) > self.param_index:
            arg = node.args[self.param_index]
            # If the argument is a Name, look up in our recorded assignments
            if isinstance(arg.value, cst.Name):
                var_name = arg.value.value
                if var_name in self.getter_assignments:
                    self.getter_method_name = self.getter_assignments[var_name]

        return True


# Register the command
register_command(ReplaceParameterWithMethodCallCommand)
