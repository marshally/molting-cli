"""LocalVariableAnalyzer for detecting local variable usage and scope.

This utility helps transformers understand which variables are local to a function
vs passed as parameters, enabling proper parameter passing when extracting code
that uses local variables.
"""

import libcst as cst


class LocalVariableAnalyzer(cst.CSTVisitor):
    """Analyzes local variables and their usage within a function.

        Use this visitor to:
        - Identify which variables are local to a function (defined via assignment)
        - Identify function parameters
        - Determine which variables are used in a specific code block
        - Understand variable scope and dependencies

        Example:
            code = '''
    def process(param1):
        local_var = 10
        result = local_var + param1
        return result
    '''
            module = cst.parse_module(code)
            analyzer = LocalVariableAnalyzer(module, "", "process")
            locals = analyzer.get_local_variables()  # ["local_var", "result"]
            params = analyzer.get_parameters()  # ["param1"]
            used = analyzer.get_variables_used_in_range(4, 4)  # Variables used in return
    """

    def __init__(self, module: cst.Module, class_name: str, function_name: str) -> None:
        """Initialize the analyzer.

        Args:
            module: The CST module to analyze
            class_name: Name of the class (empty string for module-level functions)
            function_name: Name of the function to analyze
        """
        self.module = module
        self.class_name = class_name
        self.function_name = function_name
        self._in_target_function = False
        self._in_target_class = False
        self._target_function_node: cst.FunctionDef | None = None
        self._local_variables: list[str] = []
        self._parameters: list[str] = []
        self._class_depth = 0
        self._function_depth = 0
        # Store all statements with their line numbers for range-based analysis
        self._function_statements: list[tuple[cst.BaseStatement, int]] = []

    def get_local_variables(self) -> list[str]:
        """Get all local variables defined in the target function.

        Returns:
            List of unique local variable names (not including parameters)
        """
        if not self._local_variables and not self._parameters:
            self.module.visit(self)
        return self._local_variables

    def get_parameters(self) -> list[str]:
        """Get all parameter names for the target function.

        Returns:
            List of parameter names in order
        """
        if not self._parameters and not self._local_variables:
            self.module.visit(self)
        return self._parameters

    def get_variables_used_in_range(self, start_line: int, end_line: int) -> list[str]:
        """Get all variables used in a specific line range within the function.

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            List of unique variable names used in that range
        """
        # Collect variables from the code within the range
        visitor = VariableUsageCollector()

        # Parse the function to understand line positions
        if not self._target_function_node:
            self.module.visit(self)

        # Visit statements in the target function and collect those in range
        if self._target_function_node and self._target_function_node.body.body:
            for stmt in self._target_function_node.body.body:
                # This is a simplified approach - collect all used variables
                stmt.visit(visitor)

        return visitor.used_variables

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name and self._class_depth == 0:
            self._in_target_class = True
            self._class_depth += 1
            return True
        elif self._in_target_class:
            self._class_depth += 1
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from target class."""
        if self._in_target_class:
            self._class_depth -= 1
            if self._class_depth == 0:
                self._in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target function and collect parameters."""
        # For module-level functions
        if not self.class_name and node.name.value == self.function_name:
            self._in_target_function = True
            self._target_function_node = node
            self._collect_parameters(node)
            return True

        # For class methods
        if self._in_target_class and node.name.value == self.function_name:
            self._in_target_function = True
            self._target_function_node = node
            self._collect_parameters(node)
            return True

        # Skip nested functions if we're already in the target
        if self._in_target_function:
            self._function_depth += 1
            return False

        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from target function."""
        if self._in_target_function and node.name.value == self.function_name:
            self._in_target_function = False

    def _collect_parameters(self, node: cst.FunctionDef) -> None:
        """Collect parameter names from a function definition.

        Args:
            node: The function definition node
        """
        for param in node.params.params:
            param_name = param.name.value
            # Skip 'self' for instance methods
            if param_name != "self":
                self._parameters.append(param_name)

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Collect local variables from assignments."""
        if self._in_target_function and not self._function_depth:
            for target in node.targets:
                self._extract_names_from_target(target.target)
        return True

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:  # noqa: N802
        """Collect local variables from annotated assignments."""
        if self._in_target_function and not self._function_depth:
            self._extract_names_from_target(node.target)
        return True

    def visit_For(self, node: cst.For) -> bool:  # noqa: N802
        """Collect loop variables from for statements."""
        if self._in_target_function and not self._function_depth:
            self._extract_names_from_target(node.target)
        return True

    def visit_With(self, node: cst.With) -> bool:  # noqa: N802
        """Collect variables from with statements."""
        if self._in_target_function and not self._function_depth:
            for item in node.items:
                if item.asname:
                    # Extract variable name from 'as' clause
                    if isinstance(item.asname.name, cst.Name):
                        var_name = item.asname.name.value
                        if var_name not in self._local_variables:
                            self._local_variables.append(var_name)
        return True

    def visit_ExceptHandler(self, node: cst.ExceptHandler) -> bool:  # noqa: N802
        """Collect exception handler variables."""
        if self._in_target_function and not self._function_depth:
            if node.name:
                # node.name is an AsName object, extract the name
                if isinstance(node.name, cst.AsName):
                    var_name = node.name.name.value  # type: ignore[union-attr]
                    if var_name not in self._local_variables:
                        self._local_variables.append(var_name)
        return True

    def _extract_names_from_target(self, target: cst.BaseAssignTargetExpression) -> None:
        """Extract variable names from assignment targets.

        Args:
            target: The assignment target node
        """
        if isinstance(target, cst.Name):
            var_name = target.value
            # Don't add parameters as local variables
            if var_name not in self._parameters and var_name not in self._local_variables:
                self._local_variables.append(var_name)
        elif isinstance(target, cst.Tuple) or isinstance(target, cst.List):
            # Handle tuple unpacking: a, b = ...
            for element in target.elements:
                if isinstance(element, cst.Element):
                    self._extract_names_from_target(element.value)  # type: ignore[arg-type]
        elif isinstance(target, cst.Attribute):
            # Skip self.attribute assignments - these are instance variables
            pass
        elif isinstance(target, cst.Subscript):
            # Skip subscript assignments like x[0] = ...
            pass


class VariableUsageCollector(cst.CSTVisitor):
    """Collector for all variable references in code."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.used_variables: list[str] = []

    def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802
        """Collect variable names used in expressions."""
        var_name = node.value
        # Skip Python keywords and builtins
        if var_name not in self.used_variables and not self._is_builtin(var_name):
            self.used_variables.append(var_name)
        return True

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # noqa: N802
        """Skip processing of attribute accesses to focus on base variables."""
        # We don't want to collect attribute names, just the base object
        return True

    @staticmethod
    def _is_builtin(name: str) -> bool:
        """Check if a name is a Python builtin or keyword.

        Args:
            name: Variable name to check

        Returns:
            True if it's a builtin/keyword, False otherwise
        """
        builtins = {
            "True",
            "False",
            "None",
            "self",
            "cls",
            "Exception",
            "ValueError",
            "TypeError",
            "AttributeError",
        }
        return name in builtins
