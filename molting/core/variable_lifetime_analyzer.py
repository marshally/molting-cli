"""VariableLifetimeAnalyzer for tracking variable lifetimes and scope boundaries.

This utility helps transformers understand where variables are defined and used,
enabling safe code extraction and refactoring.
"""

from dataclasses import dataclass
from typing import Any

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider


@dataclass
class VariableLifetime:
    """Represents the lifetime of a variable within a scope."""

    name: str
    first_definition: int  # line number
    last_use: int  # line number
    scope_start: int
    scope_end: int


class VariableLifetimeAnalyzer:
    """Analyzes variable lifetimes within a function.

        Use this analyzer to:
        - Track where variables are first defined
        - Track where variables are last used
        - Determine scope boundaries
        - Check if variables are used before/after specific lines

        Example:
            code = '''
    def process():
        x = 10
        y = x + 5
        return y
    '''
            module = cst.parse_module(code)
            analyzer = VariableLifetimeAnalyzer(module, None, "process")

            first_def = analyzer.get_first_definition("x")  # 3
            last_use = analyzer.get_last_use("x")  # 4
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
        self._definitions: dict[str, int] = {}
        self._uses: dict[str, list[int]] = {}
        self._scope_start: int | None = None
        self._scope_end: int | None = None
        self._analyzed = False

    def get_first_definition(self, variable_name: str) -> int | None:
        """Get line where variable is first defined.

        Args:
            variable_name: Name of the variable to look up

        Returns:
            Line number of first definition, or None if not found
        """
        self._ensure_analyzed()
        return self._definitions.get(variable_name)

    def get_last_use(self, variable_name: str) -> int | None:
        """Get line where variable is last used.

        Args:
            variable_name: Name of the variable to look up

        Returns:
            Line number of last use, or None if not found
        """
        self._ensure_analyzed()
        uses = self._uses.get(variable_name, [])
        return max(uses) if uses else None

    def get_lifetime(self, variable_name: str) -> VariableLifetime | None:
        """Get the lifetime info for a variable.

        Args:
            variable_name: Name of the variable to look up

        Returns:
            VariableLifetime object, or None if variable not found
        """
        self._ensure_analyzed()

        first_def = self.get_first_definition(variable_name)
        if first_def is None:
            return None

        last_use = self.get_last_use(variable_name)
        if last_use is None:
            return None

        return VariableLifetime(
            name=variable_name,
            first_definition=first_def,
            last_use=last_use,
            scope_start=self._scope_start or 1,
            scope_end=self._scope_end or 999999,
        )

    def is_used_before(self, variable_name: str, line: int) -> bool:
        """Check if variable is used before given line.

        Args:
            variable_name: Name of the variable
            line: Line number to check against

        Returns:
            True if variable is used before the line, False otherwise
        """
        self._ensure_analyzed()
        uses = self._uses.get(variable_name, [])
        return any(use < line for use in uses)

    def is_used_after(self, variable_name: str, line: int) -> bool:
        """Check if variable is used after given line.

        Args:
            variable_name: Name of the variable
            line: Line number to check against

        Returns:
            True if variable is used after the line, False otherwise
        """
        self._ensure_analyzed()
        uses = self._uses.get(variable_name, [])
        return any(use > line for use in uses)

    def get_all_lifetimes(self) -> dict[str, VariableLifetime]:
        """Get lifetime info for all variables in the function.

        Returns:
            Dictionary mapping variable names to VariableLifetime objects
        """
        self._ensure_analyzed()

        lifetimes = {}
        for var_name in self._definitions.keys():
            lifetime = self.get_lifetime(var_name)
            if lifetime:
                lifetimes[var_name] = lifetime

        return lifetimes

    def _ensure_analyzed(self) -> None:
        """Ensure the module has been analyzed."""
        if not self._analyzed:
            wrapper = MetadataWrapper(self.module)
            visitor = _LifetimeVisitor(self.class_name, self.function_name)
            wrapper.visit(visitor)
            self._definitions = visitor.definitions
            self._uses = visitor.uses
            self._scope_start = visitor.scope_start
            self._scope_end = visitor.scope_end
            self._analyzed = True


class _LifetimeVisitor(cst.CSTVisitor):
    """Visitor to collect variable definitions and uses."""

    METADATA_DEPENDENCIES = (PositionProvider,)

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
        self.uses: dict[str, list[int]] = {}
        self.scope_start: int | None = None
        self.scope_end: int | None = None
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
            self._capture_scope(node)
            return True

        # Class method
        if self._in_target_class and node.name.value == self.function_name:
            self._in_target_function = True
            self._function_depth = 0
            self._capture_scope(node)
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

    def _capture_scope(self, node: cst.FunctionDef) -> None:
        """Capture the scope boundaries of the function."""
        try:
            pos = self.get_metadata(PositionProvider, node)
            self.scope_start = pos.start.line
            self.scope_end = pos.end.line
        except KeyError:
            pass

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Track assignments (definitions)."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)

            # First, record reads from the right-hand side
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self._record_use(name, line)

            # Then record writes to left-hand side
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
                    self._record_use(name, line)

            # Record write to left-hand side
            if isinstance(node.target, cst.Name):
                name = node.target.value
                if name not in self.definitions:
                    self.definitions[name] = line
        return True

    def visit_AugAssign(self, node: cst.AugAssign) -> bool:  # noqa: N802
        """Track augmented assignments."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)

            # Augmented assignment uses the variable
            if isinstance(node.target, cst.Name):
                var_name = node.target.value
                self._record_use(var_name, line)

                # Also record as definition if first time
                if var_name not in self.definitions:
                    self.definitions[var_name] = line

            # Also record reads from right-hand side
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self._record_use(name, line)
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

            # Iterator is used
            reader = _NameCollector()
            node.iter.visit(reader)
            for name in reader.names:
                self._record_use(name, line)
        return True

    def visit_Return(self, node: cst.Return) -> bool:  # noqa: N802
        """Track variable reads in return statements."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            if node.value:
                reader = _NameCollector()
                node.value.visit(reader)
                for name in reader.names:
                    self._record_use(name, line)
        return True

    def visit_Expr(self, node: cst.Expr) -> bool:  # noqa: N802
        """Track variable reads in expression statements."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self._record_use(name, line)
        return True

    def _record_use(self, var_name: str, line: int) -> None:
        """Record a use of a variable at a line."""
        if var_name not in self.uses:
            self.uses[var_name] = []
        self.uses[var_name].append(line)

    def _get_line(self, node: cst.CSTNode) -> int:
        """Get the line number for a CST node."""
        try:
            pos: Any = self.get_metadata(PositionProvider, node)
            return int(pos.start.line)
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
