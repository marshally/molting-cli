"""Reusable CST visitor classes."""

import libcst as cst


class SelfFieldCollector(cst.CSTVisitor):
    """Collects all self.field references in a node.

    Example:
        collector = SelfFieldCollector(exclude_fields={"target_field"})
        method.visit(collector)
        fields = collector.collected_fields
    """

    def __init__(self, exclude_fields: set[str] | None = None) -> None:
        """Initialize the collector.

        Args:
            exclude_fields: Set of field names to exclude from collection
        """
        self.collected_fields: list[str] = []
        self.exclude_fields = exclude_fields or set()

    def visit_Attribute(self, node: cst.Attribute) -> None:  # noqa: N802
        """Visit attribute access to find self.field references."""
        if isinstance(node.value, cst.Name) and node.value.value == "self":
            field_name = node.attr.value
            if field_name not in self.collected_fields and field_name not in self.exclude_fields:
                self.collected_fields.append(field_name)


class SelfFieldChecker(cst.CSTVisitor):
    """Checks if a node accesses any specified self fields.

    This is a boolean checking version of SelfFieldCollector that can short-circuit
    traversal after finding the first match, avoiding unnecessary traversal.

    Example:
        checker = SelfFieldChecker(target_fields={"employee", "age"})
        node.visit(checker)
        if checker.found:
            print("Node accesses one of the target fields")
    """

    def __init__(self, target_fields: set[str]) -> None:
        """Initialize the checker.

        Args:
            target_fields: Set of field names to check for
        """
        self.target_fields = target_fields
        self.found = False

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # noqa: N802
        """Visit attribute access to check for target self fields.

        Returns:
            False to stop traversal if a match is found, otherwise True.
        """
        if isinstance(node.value, cst.Name) and node.value.value == "self":
            field_name = node.attr.value
            if field_name in self.target_fields:
                self.found = True
                return False  # Stop traversal
        return True


class VariableConflictChecker(cst.CSTVisitor):
    """Check if a variable name already exists in a function scope.

    Use this to detect name conflicts before introducing new variables.

    Example:
        checker = VariableConflictChecker("calculate_total", "base_price")
        module.visit(checker)
        if checker.has_conflict:
            raise ValueError(f"Variable 'base_price' already exists")
    """

    def __init__(self, function_name: str, variable_name: str) -> None:
        """Initialize the checker.

        Args:
            function_name: Name of the function to check
            variable_name: Variable name to check for conflicts
        """
        self.function_name = function_name
        self.variable_name = variable_name
        self.has_conflict = False
        self._in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target function."""
        if node.name.value == self.function_name:
            self._in_target_function = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from target function."""
        if node.name.value == self.function_name:
            self._in_target_function = False

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Check assignments for the conflicting variable name."""
        if not self._in_target_function:
            return True

        for target in node.targets:
            if isinstance(target.target, cst.Name) and target.target.value == self.variable_name:
                self.has_conflict = True
        return True

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:  # noqa: N802
        """Check annotated assignments for conflicts."""
        if not self._in_target_function:
            return True

        if isinstance(node.target, cst.Name) and node.target.value == self.variable_name:
            self.has_conflict = True
        return True


class MultiVariableConflictChecker(cst.CSTVisitor):
    """Check if any of multiple variable names exist in a function scope.

    Use this when a refactoring generates multiple variable names that could conflict.

    Example:
        checker = MultiVariableConflictChecker(
            "calculate_distance",
            ["primary_acc", "secondary_acc"]
        )
        module.visit(checker)
        if checker.conflicting_name:
            raise ValueError(f"Variable '{checker.conflicting_name}' already exists")
    """

    def __init__(self, function_name: str, variable_names: list[str]) -> None:
        """Initialize the checker.

        Args:
            function_name: Name of the function to check
            variable_names: List of variable names to check for conflicts
        """
        self.function_name = function_name
        self.variable_names = set(variable_names)
        self.conflicting_name: str | None = None
        self._in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target function."""
        if node.name.value == self.function_name:
            self._in_target_function = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from target function."""
        if node.name.value == self.function_name:
            self._in_target_function = False

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Check assignments for conflicting variable names."""
        if not self._in_target_function:
            return True

        for target in node.targets:
            if isinstance(target.target, cst.Name) and target.target.value in self.variable_names:
                self.conflicting_name = target.target.value
        return True


class MethodConflictChecker(cst.CSTVisitor):
    """Check if a method name already exists in a class.

    Use this before creating new methods via refactoring.

    Example:
        checker = MethodConflictChecker("Order", "base_price")
        module.visit(checker)
        if checker.has_conflict:
            raise ValueError(f"Method 'base_price' already exists in class 'Order'")
    """

    def __init__(self, class_name: str, method_name: str) -> None:
        """Initialize the checker.

        Args:
            class_name: Name of the class to check
            method_name: Method name to check for conflicts
        """
        self.class_name = class_name
        self.method_name = method_name
        self.has_conflict = False
        self._in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name:
            self._in_target_class = True
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from target class."""
        if node.name.value == self.class_name:
            self._in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Check if this method has the conflicting name."""
        if self._in_target_class and node.name.value == self.method_name:
            self.has_conflict = True
        return True


class FieldConflictChecker(cst.CSTVisitor):
    """Check if a field name already exists in a class.

    Use this before moving or creating fields via refactoring.
    Checks for self.field_name assignments in __init__.

    Example:
        checker = FieldConflictChecker("AccountType", "interest_rate")
        module.visit(checker)
        if checker.has_conflict:
            raise ValueError(f"Field 'interest_rate' already exists in class 'AccountType'")
    """

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the checker.

        Args:
            class_name: Name of the class to check
            field_name: Field name to check for conflicts
        """
        self.class_name = class_name
        self.field_name = field_name
        self.has_conflict = False
        self._in_target_class = False
        self._in_init = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name:
            self._in_target_class = True
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from target class."""
        if node.name.value == self.class_name:
            self._in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into __init__ method."""
        if self._in_target_class and node.name.value == "__init__":
            self._in_init = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from __init__ method."""
        if self._in_target_class and node.name.value == "__init__":
            self._in_init = False

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Check for self.field_name assignments."""
        if not self._in_init:
            return True

        for target in node.targets:
            if isinstance(target.target, cst.Attribute):
                attr = target.target
                if (
                    isinstance(attr.value, cst.Name)
                    and attr.value.value == "self"
                    and attr.attr.value == self.field_name
                ):
                    self.has_conflict = True
        return True


class ClassConflictChecker(cst.CSTVisitor):
    """Check if a class name already exists at module level.

    Use this before creating new classes via refactoring.

    Example:
        checker = ClassConflictChecker("Gamma")
        module.visit(checker)
        if checker.has_conflict:
            raise ValueError(f"Class 'Gamma' already exists in the module")
    """

    def __init__(self, class_name: str) -> None:
        """Initialize the checker.

        Args:
            class_name: Class name to check for conflicts
        """
        self.class_name = class_name
        self.has_conflict = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Check if this class has the conflicting name."""
        if node.name.value == self.class_name:
            self.has_conflict = True
        return True


class FunctionConflictChecker(cst.CSTVisitor):
    """Check if a function name already exists at module level.

    Use this before creating new module-level functions via refactoring.

    Example:
        checker = FunctionConflictChecker("normalize_string")
        module.visit(checker)
        if checker.has_conflict:
            raise ValueError(f"Function 'normalize_string' already exists")
    """

    def __init__(self, function_name: str) -> None:
        """Initialize the checker.

        Args:
            function_name: Function name to check for conflicts
        """
        self.function_name = function_name
        self.has_conflict = False
        self._depth = 0  # Track nesting depth to only check module-level

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into class (increases depth)."""
        self._depth += 1
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from class."""
        self._depth -= 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Check if this is a module-level function with the conflicting name."""
        if self._depth == 0 and node.name.value == self.function_name:
            self.has_conflict = True
        self._depth += 1
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from function."""
        self._depth -= 1


class DelegatingMethodChecker(cst.CSTVisitor):
    """Check if a method in a class is a delegating method.

    A delegating method is one that simply calls through to another object's
    method of the same name (e.g., `return self.delegate.method()`).

    This is useful for inline-class refactoring to distinguish between:
    - Delegating methods (should be replaced, not a conflict)
    - Independent methods with same name (true conflict)

    Example:
        checker = DelegatingMethodChecker("Person", "get_telephone_number", "office_telephone")
        module.visit(checker)
        if checker.is_delegating:
            # Method just delegates to self.office_telephone.get_telephone_number()
            pass
    """

    def __init__(self, class_name: str, method_name: str, delegate_field: str) -> None:
        """Initialize the checker.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to check
            delegate_field: Field name that delegates to the source class
        """
        self.class_name = class_name
        self.method_name = method_name
        self.delegate_field = delegate_field
        self.is_delegating = False
        self._in_target_class = False
        self._in_target_method = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name:
            self._in_target_class = True
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from target class."""
        if node.name.value == self.class_name:
            self._in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target method and check for delegation."""
        if self._in_target_class and node.name.value == self.method_name:
            self._in_target_method = True
            self._check_is_delegating(node)
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from target method."""
        if self._in_target_class and node.name.value == self.method_name:
            self._in_target_method = False

    def _check_is_delegating(self, method: cst.FunctionDef) -> None:
        """Check if the method body is just a delegation call.

        Delegation patterns we recognize:
        - return self.delegate.method(...)
        - return self.delegate.method  (for properties)
        - self.delegate.method(...)  (void delegation)
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return

        body = method.body.body
        if len(body) != 1:
            return

        stmt = body[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return

        if len(stmt.body) != 1:
            return

        inner = stmt.body[0]

        # Check for: return self.delegate.method(...) or return self.delegate.method
        if isinstance(inner, cst.Return) and inner.value is not None:
            self._check_delegation_expression(inner.value)
        # Check for: self.delegate.method(...)
        elif isinstance(inner, cst.Expr):
            self._check_delegation_expression(inner.value)

    def _check_delegation_expression(self, expr: cst.BaseExpression) -> None:
        """Check if expression is a delegation to the delegate field."""
        # Handle: self.delegate.method(...)
        if isinstance(expr, cst.Call):
            func = expr.func
            if self._is_delegate_attribute(func):
                self.is_delegating = True
        # Handle: self.delegate.method (property access)
        elif self._is_delegate_attribute(expr):
            self.is_delegating = True

    def _is_delegate_attribute(self, node: cst.BaseExpression) -> bool:
        """Check if node is self.delegate_field.method_name."""
        if not isinstance(node, cst.Attribute):
            return False

        # Check the attribute name matches the method name
        if node.attr.value != self.method_name:
            return False

        # Check the value is self.delegate_field
        value = node.value
        if not isinstance(value, cst.Attribute):
            return False

        if not isinstance(value.value, cst.Name) or value.value.value != "self":
            return False

        if value.attr.value != self.delegate_field:
            return False

        return True
