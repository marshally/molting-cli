"""Split Temporary Variable refactoring using libcst."""

from pathlib import Path
import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class SplitTemporaryVariable(RefactoringBase):
    """Split a temporary variable assigned multiple times.

    From Martin Fowler's catalog: "You have a temporary variable assigned to
    more than once, but is not a loop variable nor a collecting temporary
    variable. Make a separate temporary variable for each assignment."
    """

    def __init__(self, file_path: str, target: str):
        """Initialize the Split Temporary Variable refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function and variable (e.g., "calculate::temp" or "ClassName::method::temp")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

        # Parse target: "function_name::var_name" or "ClassName::method_name::var_name"
        parts = target.split("::")
        if len(parts) < 2:
            raise ValueError(f"Invalid target format: {target}. Expected 'function::variable' or 'Class::method::variable'")

        self.var_name = parts[-1]  # Last part is always the variable name

        if len(parts) == 2:
            # Simple function target
            self.func_name = parts[0]
            self.class_name = None
        elif len(parts) == 3:
            # Class method target
            self.class_name = parts[0]
            self.func_name = parts[1]
        else:
            raise ValueError(f"Invalid target format: {target}. Expected 'function::variable' or 'Class::method::variable'")

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code
        """
        self.source = source

        # Parse the source code into a CST
        module = cst.parse_module(source)

        # Transform the module
        transformer = TemporaryVariableSplitter(self.func_name, self.class_name, self.var_name)
        modified_tree = module.visit(transformer)

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            cst.parse_module(source)
            return True
        except Exception:
            return False


class TemporaryVariableSplitter(cst.CSTTransformer):
    """Transform code to split temporary variables."""

    def __init__(self, func_name: str, class_name: str | None, var_name: str):
        """Initialize the splitter.

        Args:
            func_name: Name of the function to refactor
            class_name: Name of the class (if method), or None
            var_name: Name of the variable to split
        """
        self.func_name = func_name
        self.class_name = class_name
        self.var_name = var_name
        self.assignment_count = {}  # Maps assignment index to new variable name

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Process the target function to split temporary variables."""
        # Check if this is the function we're looking for
        if original_node.name.value == self.func_name:
            # If we have a class name, we'll handle it in leave_ClassDef
            if self.class_name is None:
                # Process the function body
                new_body = self._process_function_body(original_node, updated_node)
                return updated_node.with_changes(body=new_body)

        return updated_node

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Process class definitions to find target methods."""
        if original_node.name.value == self.class_name:
            # Process the class body
            new_body = updated_node.body
            if isinstance(new_body, cst.IndentedBlock):
                new_stmts = []
                for stmt in new_body.body:
                    if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.func_name:
                        # Process this method
                        transformer = TemporaryVariableSplitter(self.func_name, None, self.var_name)
                        stmt = stmt.visit(transformer)
                    new_stmts.append(stmt)
                new_body = new_body.with_changes(body=new_stmts)
                return updated_node.with_changes(body=new_body)

        return updated_node

    def _process_function_body(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.IndentedBlock:
        """Process the function body to split temporary variables."""
        body = updated_node.body

        if not isinstance(body, cst.IndentedBlock):
            return body

        # First pass: find all assignments to the target variable
        assignments = self._find_assignments(body.body)

        # If less than 2 assignments, nothing to split
        if len(assignments) < 2:
            return body

        # Map each assignment index to a new variable name
        self.assignment_count = {}
        for i in range(len(assignments)):
            if i == 0:
                self.assignment_count[i] = self.var_name
            else:
                self.assignment_count[i] = f"{self.var_name}_{i + 1}"

        # Transform the body: process statements sequentially
        new_stmts = []
        replacer = VariableReplacer(self.var_name, assignments, self.assignment_count)

        # Process each statement
        for stmt_idx, stmt in enumerate(body.body):
            # Visit the statement with context about which statement index we're in
            replacer.set_stmt_index(stmt_idx)
            new_stmt = stmt.visit(replacer)
            new_stmts.append(new_stmt)

        return body.with_changes(body=new_stmts)

    def _find_assignments(self, statements: list) -> list:
        """Find all assignments to the target variable.

        Returns:
            List of statement indices where the variable is assigned
        """
        assignments = []
        stmt_index = 0

        for stmt in statements:
            if isinstance(stmt, cst.SimpleStatementLine):
                for s in stmt.body:
                    if isinstance(s, cst.Assign):
                        for target in s.targets:
                            if isinstance(target.target, cst.Name) and target.target.value == self.var_name:
                                assignments.append(stmt_index)
                stmt_index += 1
            else:
                stmt_index += 1

        return assignments


class VariableReplacer(cst.CSTTransformer):
    """Replace variable names and usages based on assignments."""

    def __init__(self, var_name: str, assignments: list, assignment_count: dict):
        """Initialize the replacer.

        Args:
            var_name: Name of the original variable
            assignments: List of statement indices where variable is assigned
            assignment_count: Maps assignment index to new variable name
        """
        self.var_name = var_name
        self.assignments = assignments
        self.assignment_count = assignment_count
        self.current_stmt_index = -1  # Current statement index being visited
        self.current_assignment_index = -1  # Which assignment index we're currently in

    def set_stmt_index(self, stmt_index: int):
        """Set the current statement index."""
        self.current_stmt_index = stmt_index
        # Determine if this statement contains an assignment
        if stmt_index in self.assignments:
            self.current_assignment_index = self.assignments.index(stmt_index)

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        """Replace assignment targets."""
        target = original_node.targets[0].target
        if isinstance(target, cst.Name) and target.value == self.var_name:
            # This is an assignment to our target variable
            if self.current_stmt_index in self.assignments:
                assignment_idx = self.assignments.index(self.current_stmt_index)
                new_var_name = self.assignment_count[assignment_idx]
                # Replace the target variable name
                new_target = updated_node.targets[0].with_changes(target=cst.Name(new_var_name))
                return updated_node.with_changes(targets=[new_target])

        return updated_node

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        """Replace variable usages based on which assignment scope we're in."""
        if original_node.value == self.var_name and self.current_assignment_index >= 0:
            new_var_name = self.assignment_count[self.current_assignment_index]
            return updated_node.with_changes(value=new_var_name)

        return updated_node
