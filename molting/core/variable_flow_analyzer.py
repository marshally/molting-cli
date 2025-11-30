"""VariableFlowAnalyzer for tracking variable reads/writes in code regions.

This utility helps transformers understand variable data flow to determine
which variables need to be passed as parameters or returned from extracted
code regions.
"""

from dataclasses import dataclass

import libcst as cst


@dataclass
class VariableAccess:
    """Represents a variable access (read or write) at a specific line."""

    name: str
    line: int
    is_read: bool
    is_write: bool


class VariableFlowAnalyzer:
    """Analyzes variable flow to determine inputs/outputs for code regions.

    Use this analyzer to:
    - Track which variables are read in a line range
    - Track which variables are written in a line range
    - Determine inputs needed for extracted code (read before written)
    - Determine outputs from extracted code (written and used later)

    Example:
        code = '''
def process(param):
    x = 10
    y = x + param
    return y
'''
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Get variables read in line 4 (y = x + param)
        reads = analyzer.get_reads_in_range(4, 4)  # ["x", "param"]

        # Get inputs needed for lines 3-4
        inputs = analyzer.get_inputs_for_region(3, 4)  # ["param"]
    """

    def __init__(
        self, module: cst.Module, class_name: str | None, function_name: str
    ) -> None:
        """Initialize the analyzer.

        Args:
            module: The CST module to analyze
            class_name: Name of the class (None or "" for module-level functions)
            function_name: Name of the function to analyze
        """
        self.module = module
        self.class_name = class_name or ""
        self.function_name = function_name
        self._accesses: list[VariableAccess] = []
        self._analyzed = False

    def get_reads_in_range(self, start_line: int, end_line: int) -> list[str]:
        """Get variables read within a line range.

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            List of unique variable names read in that range
        """
        self._ensure_analyzed()

        reads = []
        for access in self._accesses:
            if start_line <= access.line <= end_line and access.is_read:
                if access.name not in reads:
                    reads.append(access.name)
        return reads

    def get_writes_in_range(self, start_line: int, end_line: int) -> list[str]:
        """Get variables written within a line range.

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            List of unique variable names written in that range
        """
        self._ensure_analyzed()

        writes = []
        for access in self._accesses:
            if start_line <= access.line <= end_line and access.is_write:
                if access.name not in writes:
                    writes.append(access.name)
        return writes

    def get_inputs_for_region(self, start_line: int, end_line: int) -> list[str]:
        """Get variables that must be passed INTO a region (read before written).

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            List of variable names that are inputs to the region
        """
        self._ensure_analyzed()

        reads = self.get_reads_in_range(start_line, end_line)
        writes = self.get_writes_in_range(start_line, end_line)

        # Variables that are read before being written in the region
        inputs = []
        for var in reads:
            # Check if this variable is written before it's first read in the region
            first_read_line = self._get_first_read_in_range(var, start_line, end_line)
            first_write_line = self._get_first_write_in_range(var, start_line, end_line)

            if first_read_line is not None:
                if first_write_line is None or first_read_line < first_write_line:
                    if var not in inputs:
                        inputs.append(var)

        return inputs

    def get_outputs_from_region(self, start_line: int, end_line: int) -> list[str]:
        """Get variables that flow OUT of a region (written and used later).

        Args:
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed)

        Returns:
            List of variable names that are outputs from the region
        """
        self._ensure_analyzed()

        writes = self.get_writes_in_range(start_line, end_line)

        # Variables that are written in the region and used after
        outputs = []
        for var in writes:
            # Check if variable is used after the region
            if self._is_used_after_line(var, end_line):
                if var not in outputs:
                    outputs.append(var)

        return outputs

    def _ensure_analyzed(self) -> None:
        """Ensure the module has been analyzed."""
        if not self._analyzed:
            # Use MetadataWrapper to provide position information
            wrapper = cst.metadata.MetadataWrapper(self.module)
            visitor = _VariableAccessVisitor(self.class_name, self.function_name)
            wrapper.visit(visitor)
            self._accesses = visitor.accesses
            self._analyzed = True

    def _get_first_read_in_range(
        self, var_name: str, start_line: int, end_line: int
    ) -> int | None:
        """Get the first line where a variable is read in a range."""
        for access in self._accesses:
            if (
                access.name == var_name
                and access.is_read
                and start_line <= access.line <= end_line
            ):
                return access.line
        return None

    def _get_first_write_in_range(
        self, var_name: str, start_line: int, end_line: int
    ) -> int | None:
        """Get the first line where a variable is written in a range."""
        for access in self._accesses:
            if (
                access.name == var_name
                and access.is_write
                and start_line <= access.line <= end_line
            ):
                return access.line
        return None

    def _is_used_after_line(self, var_name: str, line: int) -> bool:
        """Check if a variable is used (read) after a given line."""
        for access in self._accesses:
            if access.name == var_name and access.is_read and access.line > line:
                return True
        return False


class _VariableAccessVisitor(cst.CSTVisitor):
    """Visitor to collect all variable accesses in a function."""

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
        self.accesses: list[VariableAccess] = []
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
        """Track assignments (writes)."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            # First, record reads from the right-hand side
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self.accesses.append(
                    VariableAccess(name=name, line=line, is_read=True, is_write=False)
                )

            # Then record writes to left-hand side
            for target in node.targets:
                writer = _AssignTargetCollector()
                target.visit(writer)
                for name in writer.names:
                    self.accesses.append(
                        VariableAccess(
                            name=name, line=line, is_read=False, is_write=True
                        )
                    )
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
                    self.accesses.append(
                        VariableAccess(
                            name=name, line=line, is_read=True, is_write=False
                        )
                    )

            # Record write to left-hand side
            if isinstance(node.target, cst.Name):
                self.accesses.append(
                    VariableAccess(
                        name=node.target.value, line=line, is_read=False, is_write=True
                    )
                )
        return True

    def visit_AugAssign(self, node: cst.AugAssign) -> bool:  # noqa: N802
        """Track augmented assignments (+=, -=, etc)."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            # Augmented assignment is both read and write
            if isinstance(node.target, cst.Name):
                var_name = node.target.value
                self.accesses.append(
                    VariableAccess(name=var_name, line=line, is_read=True, is_write=False)
                )
                self.accesses.append(
                    VariableAccess(name=var_name, line=line, is_read=False, is_write=True)
                )

            # Also record reads from right-hand side
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self.accesses.append(
                    VariableAccess(name=name, line=line, is_read=True, is_write=False)
                )
        return True

    def visit_Return(self, node: cst.Return) -> bool:  # noqa: N802
        """Track variable reads in return statements."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            if node.value:
                reader = _NameCollector()
                node.value.visit(reader)
                for name in reader.names:
                    self.accesses.append(
                        VariableAccess(
                            name=name, line=line, is_read=True, is_write=False
                        )
                    )
        return True

    def visit_Expr(self, node: cst.Expr) -> bool:  # noqa: N802
        """Track variable reads in expression statements."""
        if self._in_target_function and self._function_depth == 0:
            line = self._get_line(node)
            reader = _NameCollector()
            node.value.visit(reader)
            for name in reader.names:
                self.accesses.append(
                    VariableAccess(name=name, line=line, is_read=True, is_write=False)
                )
        return True

    def _get_line(self, node: cst.CSTNode) -> int:
        """Get the line number for a CST node."""
        try:
            pos = self.get_metadata(cst.metadata.PositionProvider, node)
            return pos.start.line
        except KeyError:
            # Fallback if metadata not available
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
