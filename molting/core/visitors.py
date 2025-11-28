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
