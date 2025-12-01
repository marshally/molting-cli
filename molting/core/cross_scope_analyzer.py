"""CrossScopeAnalyzer for detecting variables used across scope boundaries.

This utility helps transformers determine which variables would need to be
captured or passed when extracting code regions.
"""

import libcst as cst


class CrossScopeAnalyzer:
    """Analyzes cross-scope variable usage for code extraction.

        Use this analyzer to:
        - Find free variables (used in region but defined outside)
        - Determine if extracted code would need closure
        - Identify variables that would be captured

        Example:
            code = '''
    def process():
        x = 10
        y = x + 5
        return y
    '''
            module = cst.parse_module(code)
            analyzer = CrossScopeAnalyzer(module, None, "process")

            # Check if lines 4-4 need closure
            needs_closure = analyzer.needs_closure(4, 4)  # True (uses x)
    """

    def __init__(self, module: cst.Module, class_name: str | None, function_name: str) -> None:
        """Initialize the analyzer.

        Args:
            module: The CST module to analyze
            class_name: Name of the class (None or "" for module-level functions)
            function_name: Name of the function to analyze
        """
        self.module = module
        self.class_name = class_name or ""
        self.function_name = function_name
        self._analyzed = False
        self._definitions: dict[str, int] = {}
        self._reads: dict[str, list[int]] = {}

    def get_free_variables(self, start_line: int, end_line: int) -> list[str]:
        """Get variables used in region but defined outside it.

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            List of variable names that are free in the region
        """
        self._ensure_analyzed()

        free_vars = []

        # Find all variables read in the region
        for var_name, read_lines in self._reads.items():
            # Check if variable is read in this region
            used_in_region = any(start_line <= line <= end_line for line in read_lines)

            if used_in_region:
                # Check if it's defined outside the region
                def_line = self._definitions.get(var_name)
                if def_line is None or def_line < start_line or def_line > end_line:
                    if var_name not in free_vars:
                        free_vars.append(var_name)

        return free_vars

    def needs_closure(self, start_line: int, end_line: int) -> bool:
        """Check if extracted region would need closure over outer variables.

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            True if region needs closure, False otherwise
        """
        free_vars = self.get_free_variables(start_line, end_line)
        return len(free_vars) > 0

    def get_captured_variables(self, start_line: int, end_line: int) -> list[str]:
        """Get variables that would be captured if region became a closure.

        This is currently equivalent to get_free_variables, but conceptually
        represents variables that would need to be in the closure's scope.

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            List of variable names that would be captured
        """
        return self.get_free_variables(start_line, end_line)

    def _ensure_analyzed(self) -> None:
        """Ensure the module has been analyzed."""
        if not self._analyzed:
            wrapper = cst.metadata.MetadataWrapper(self.module)
            visitor = _CrossScopeVisitor(self.class_name, self.function_name)
            wrapper.visit(visitor)
            self._definitions = visitor.definitions
            self._reads = visitor.reads
            self._analyzed = True


class _CrossScopeVisitor(cst.CSTVisitor):
    """Visitor to collect variable definitions and reads."""

    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(self, class_name: str, function_name: str) -> None:
        """Initialize the visitor.

        Args:
            class_name: Name of the target class
            function_name: Name of the target function
        """
        super().__init__()
        self.class_name = class_name
        self.function_name = function_name
        self.definitions: dict[str, int] = {}
        self.reads: dict[str, list[int]] = {}
        self._in_target_class = False
        self._in_target_function = False
        self._class_depth = 0
        self._function_depth = 0

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if self.class_name and node.name.value == self.class_name:
            if self._class_depth == 0:
                self._in_target_class = True
            self._class_depth += 1
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from target class."""
        if self.class_name and node.name.value == self.class_name:
            self._class_depth -= 1
            if self._class_depth == 0:
                self._in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target function."""
        # Module-level function
        if not self.class_name and node.name.value == self.function_name:
            self._in_target_function = True
            self._function_depth = 0
            return True

        # Class method
        if self._in_target_class and node.name.value == self.function_name:
            self._in_target_function = True
            self._function_depth = 0
            return True

        # Nested function
        if self._in_target_function:
            self._function_depth += 1
            return False

        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from target function."""
        if self._in_target_function:
            if self._function_depth > 0:
                self._function_depth -= 1
            elif node.name.value == self.function_name:
                self._in_target_function = False

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Track assignments (definitions)."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)

            # First, record reads from the right-hand side
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self._record_read(name, line)

            # Then record definitions on left-hand side
            for target in node.targets:
                writer = _AssignTargetCollector()
                target.visit(writer)
                for name in writer.names:
                    # Only record first definition
                    if name not in self.definitions:
                        self.definitions[name] = line
        return True

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:  # noqa: N802
        """Track annotated assignments."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)

            # Record reads from right-hand side if there is a value
            if node.value:
                reader = _NameCollector()
                node.value.visit(reader)
                for name in reader.names:
                    self._record_read(name, line)

            # Record definition on left-hand side
            if isinstance(node.target, cst.Name):
                name = node.target.value
                if name not in self.definitions:
                    self.definitions[name] = line
        return True

    def visit_AugAssign(self, node: cst.AugAssign) -> bool:  # noqa: N802
        """Track augmented assignments."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)

            # Augmented assignment reads the variable
            if isinstance(node.target, cst.Name):
                var_name = node.target.value
                self._record_read(var_name, line)

                # Also record as definition if first time
                if var_name not in self.definitions:
                    self.definitions[var_name] = line

            # Also record reads from right-hand side
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self._record_read(name, line)
        return True

    def visit_For(self, node: cst.For) -> bool:  # noqa: N802
        """Track for loop variables."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)

            # Loop target is a definition
            collector = _AssignTargetCollector()
            node.target.visit(collector)
            for name in collector.names:
                if name not in self.definitions:
                    self.definitions[name] = line

            # Iterator is read
            reader = _NameCollector()
            node.iter.visit(reader)
            for name in reader.names:
                self._record_read(name, line)
        return True

    def visit_Return(self, node: cst.Return) -> bool:  # noqa: N802
        """Track variable reads in return statements."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            if node.value:
                reader = _NameCollector()
                node.value.visit(reader)
                for name in reader.names:
                    self._record_read(name, line)
        return True

    def visit_Expr(self, node: cst.Expr) -> bool:  # noqa: N802
        """Track variable reads in expression statements."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self._record_read(name, line)
        return True

    def _record_read(self, var_name: str, line: int) -> None:
        """Record a read of a variable at a line."""
        if var_name not in self.reads:
            self.reads[var_name] = []
        self.reads[var_name].append(line)

    def _get_line(self, node: cst.CSTNode) -> int:
        """Get the line number for a CST node."""
        try:
            pos = self.get_metadata(cst.metadata.PositionProvider, node)
            return pos.start.line
        except KeyError:
            return 1


class _NameCollector(cst.CSTVisitor):
    """Collects all Name nodes (variable references)."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.names: list[str] = []

    def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802
        """Collect variable names."""
        if not self._is_builtin(node.value):
            self.names.append(node.value)
        return True

    @staticmethod
    def _is_builtin(name: str) -> bool:
        """Check if a name is a Python builtin."""
        builtins = {
            "True",
            "False",
            "None",
            "self",
            "cls",
            "len",
            "print",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "range",
            "enumerate",
            "zip",
            "hasattr",
        }
        return name in builtins


class _AssignTargetCollector(cst.CSTVisitor):
    """Collects variable names from assignment targets."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.names: list[str] = []

    def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802
        """Collect variable names from targets."""
        self.names.append(node.value)
        return True

    def visit_Attribute(self, node: cst.Attribute) -> bool:  # noqa: N802
        """Skip attributes (self.x)."""
        return False
