"""InstanceVariableTracker for detecting class method context and self references.

This utility helps transformers understand if code is inside a class method,
what self.attribute references are used, and whether extracted methods need
a self parameter.
"""

import libcst as cst


class InstanceVariableTracker(cst.CSTVisitor):
    """Tracks instance variables and detects class method context.

        Use this visitor to:
        - Detect if code is inside a class method (vs standalone function)
        - Collect all self.attribute references in a method
        - Determine if extracted code needs self parameter
        - Collect instance variables defined in __init__

        Example:
            code = '''
    class Calculator:
        def add(self, a, b):
            return a + b + self.offset
    '''
            module = cst.parse_module(code)
            tracker = InstanceVariableTracker(module, "Calculator", "add")
            if tracker.needs_self_parameter():
                # extracted methods should have self as first param
                pass
            refs = tracker.collect_self_references()  # returns ["offset"]
    """

    def __init__(self, module: cst.Module, class_name: str, method_name: str) -> None:
        """Initialize the tracker.

        Args:
            module: The CST module to analyze
            class_name: Name of the class (empty string for module-level functions)
            method_name: Name of the method or function to analyze
        """
        self.module = module
        self.class_name = class_name
        self.method_name = method_name
        self._in_target_class = False
        self._in_target_method = False
        self._target_method_node: cst.FunctionDef | None = None
        self._method_decorators: list[str] = []
        self._self_references: list[str] = []
        self._init_instance_vars: list[str] = []
        self._is_in_init = False
        self._class_depth = 0

    def is_method(self) -> bool:
        """Check if the target is a method inside a class (not static/class method).

        Returns:
            True if target is an instance method, False otherwise
        """
        self.module.visit(self)

        # If class_name is empty, it's a module-level function
        if not self.class_name:
            return False

        # If it's a static method or class method, it doesn't have self
        if self._method_decorators:
            for decorator in self._method_decorators:
                if decorator in ("staticmethod", "classmethod"):
                    return False

        # Check if the method has self as first parameter
        if self._target_method_node:
            params = self._target_method_node.params
            if params.params and len(params.params) > 0:
                first_param = params.params[0].name.value
                return first_param == "self"

        return False

    def collect_self_references(self) -> list[str]:
        """Collect all self.attribute references in the target method.

        Returns:
            List of unique attribute names accessed via self
        """
        if self._self_references:
            return self._self_references

        self._self_references = []
        self.module.visit(self)
        return self._self_references

    def needs_self_parameter(self) -> bool:
        """Determine if extracted code would need self parameter.

        Returns:
            True if code uses self.attribute or self.method(), False otherwise
        """
        return len(self.collect_self_references()) > 0

    def collect_init_instance_variables(self) -> list[str]:
        """Collect all instance variables defined in __init__.

        Returns:
            List of instance variable names (self.attr = ...)
        """
        # If we're already analyzing __init__, just return the result
        if self.method_name == "__init__":
            if self._init_instance_vars:
                return self._init_instance_vars
            # Visit to collect the variables
            self.module.visit(self)
            return self._init_instance_vars

        # Otherwise create a new tracker for __init__
        init_tracker = InstanceVariableTracker(self.module, self.class_name, "__init__")
        return init_tracker.collect_init_instance_variables()

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name and self._class_depth == 0:
            self._in_target_class = True
            self._class_depth += 1
            return True
        elif self._in_target_class and self._class_depth == 1:
            # Nested class inside target class - skip it
            self._class_depth += 1
            return False
        self._class_depth += 1
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from target class."""
        self._class_depth -= 1
        if node.name.value == self.class_name and self._class_depth == 0:
            self._in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target method."""
        # For module-level functions, check without class context
        if not self.class_name and node.name.value == self.method_name:
            self._in_target_method = True
            self._target_method_node = node
            # Collect decorators
            for decorator in node.decorators:
                if isinstance(decorator.decorator, cst.Name):
                    self._method_decorators.append(decorator.decorator.value)
            return True

        # For class methods
        if self._in_target_class and node.name.value == self.method_name:
            self._in_target_method = True
            self._target_method_node = node
            # Collect decorators
            for decorator in node.decorators:
                if isinstance(decorator.decorator, cst.Name):
                    self._method_decorators.append(decorator.decorator.value)
            # If this is __init__, also start collecting instance vars
            if self.method_name == "__init__":
                self._is_in_init = True
            return True

        # For __init__ collection when visiting for other methods
        if (
            self._in_target_class
            and node.name.value == "__init__"
            and self.method_name != "__init__"
        ):
            self._is_in_init = True
            return True

        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from target method."""
        if self._in_target_method and node.name.value == self.method_name:
            self._in_target_method = False
        if self._is_in_init and node.name.value == "__init__":
            self._is_in_init = False

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # noqa: N802
        """Collect self.attribute references."""
        if isinstance(node.value, cst.Name) and node.value.value == "self":
            attr_name = node.attr.value
            if attr_name not in self._self_references:
                self._self_references.append(attr_name)
        return True

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Collect instance variables from assignments in __init__."""
        if self._is_in_init:
            for target in node.targets:
                if isinstance(target.target, cst.Attribute):
                    attr = target.target
                    if isinstance(attr.value, cst.Name) and attr.value.value == "self":
                        var_name = attr.attr.value
                        if var_name not in self._init_instance_vars:
                            self._init_instance_vars.append(var_name)
        return True

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:  # noqa: N802
        """Collect instance variables from annotated assignments in __init__."""
        if self._is_in_init:
            if isinstance(node.target, cst.Attribute):
                attr = node.target
                if isinstance(attr.value, cst.Name) and attr.value.value == "self":
                    var_name = attr.attr.value
                    if var_name not in self._init_instance_vars:
                        self._init_instance_vars.append(var_name)
        return True
