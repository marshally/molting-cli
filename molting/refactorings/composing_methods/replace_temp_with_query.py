"""Replace Temp with Query refactoring - replace temp variable with method call."""

import ast
import re
from pathlib import Path
from typing import Optional

from rope.base.project import Project
from rope.refactor.extract import ExtractMethod as RopeExtractMethod

from molting.core.refactoring_base import RefactoringBase


class ReplaceTempWithQuery(RefactoringBase):
    """Replace a temporary variable with a method call.

    This refactoring extracts the expression assigned to a temporary variable
    into a new method, then replaces all uses of the temp variable with calls
    to the new method.
    """

    def __init__(self, file_path: str, target: str):
        """Initialize the ReplaceTempWithQuery refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target variable specification (e.g., "Order::get_price::base_price")
                    Format: ClassName::method_name::variable_name
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

        # Parse the target to extract class, method, and variable name
        self.class_name, self.method_name, self.var_name = self._parse_target()

    def _parse_target(self) -> tuple[str, str, str]:
        """Parse target in format ClassName::method_name::variable_name.

        Returns:
            Tuple of (class_name, method_name, variable_name)

        Raises:
            ValueError: If target format is invalid
        """
        parts = self.target.split("::")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid target format: {self.target}. "
                f"Expected: ClassName::method_name::variable_name"
            )
        return parts[0], parts[1], parts[2]

    def apply(self, source: str) -> str:
        """Apply the replace temp with query refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with temp variable replaced with query method
        """
        # Use the provided source code
        self.source = source

        # Write source to file so rope can read it
        self.file_path.write_text(source)

        # Parse the AST to find the variable assignment
        tree = ast.parse(source)

        # Find the method and variable
        method_node = self._find_method(tree)
        if not method_node:
            raise ValueError(
                f"Method '{self.method_name}' not found in class '{self.class_name}'"
            )

        # Find the assignment statement for the variable
        assignment_stmt = self._find_assignment(method_node)
        if not assignment_stmt:
            raise ValueError(
                f"Variable '{self.var_name}' assignment not found in method '{self.method_name}'"
            )

        # Extract the line range for the assignment
        start_line = assignment_stmt.lineno

        # Extract just the right-hand side expression into a method
        method_name_new = self.var_name

        # Create a rope project to perform the extraction
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            resource = project.get_file(self.file_path.name)

            # Calculate byte offsets for the expression
            lines = source.split("\n")

            # Find the assignment line and extract just the RHS
            assign_line = lines[start_line - 1]

            # Parse the expression from the assignment
            # Format: "    base_price = self.quantity * self.item_price"
            match = re.match(r"^(\s*)(\w+)\s*=\s*(.+)$", assign_line)
            if not match:
                raise ValueError(f"Cannot parse assignment: {assign_line}")

            expr_text = match.group(3).rstrip()

            # Calculate the offset of the expression
            expr_start = assign_line.find(expr_text)

            # Calculate absolute offset in the file
            start_offset = 0
            for i in range(start_line - 1):
                start_offset += len(lines[i]) + 1  # +1 for newline
            start_offset += expr_start

            # End offset is at the end of the expression
            end_offset = start_offset + len(expr_text)

            # Use rope to extract the expression into a method
            extract_refactor = RopeExtractMethod(
                project, resource, start_offset, end_offset
            )
            changes = extract_refactor.get_changes(method_name_new)
            project.do(changes)

            # Read the refactored content after extraction
            refactored = resource.read()

        finally:
            project.close()

        # Now replace uses of the temp variable with method calls
        # Parse the refactored code and replace temp_var with self.temp_var()
        refactored = self._replace_temp_usage(refactored)

        return refactored

    def _find_method(self, tree: ast.Module) -> Optional[ast.FunctionDef]:
        """Find the target method in the AST.

        Args:
            tree: AST module

        Returns:
            FunctionDef node for the method, or None if not found
        """
        # Find the class
        class_node = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == self.class_name:
                class_node = node
                break

        if not class_node:
            return None

        # Find the method in the class
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == self.method_name:
                return node

        return None

    def _find_assignment(
        self, method_node: ast.FunctionDef
    ) -> Optional[ast.Assign]:
        """Find the assignment statement for the temp variable.

        Args:
            method_node: FunctionDef node of the method

        Returns:
            Assign node if found, None otherwise
        """
        for stmt in method_node.body:
            if isinstance(stmt, ast.Assign):
                # Check if this assignment is for our variable
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == self.var_name:
                        return stmt
        return None

    def _replace_temp_usage(self, source: str) -> str:
        """Replace uses of the temp variable with method calls.

        Args:
            source: Source code with extracted method

        Returns:
            Source code with temp variable replaced by method calls
        """
        # Parse to find the method again (after extraction)
        tree = ast.parse(source)
        method_node = self._find_method(tree)

        if not method_node:
            return source

        lines = source.split("\n")

        # Get the method's line range
        method_start = method_node.lineno - 1  # Convert to 0-indexed
        method_end = method_node.end_lineno  # Already exclusive

        # Get all lines in the method
        method_lines = lines[method_start:method_end]

        # Find all uses of the temp variable and replace with self.method_call()
        # Need to be careful not to replace the assignment itself
        new_method_lines = []
        assignment_found = False

        for i, line in enumerate(method_lines):
            # Skip the assignment statement itself
            if i == 0 or not assignment_found:
                if re.search(rf"\b{self.var_name}\s*=", line):
                    # This is the assignment - remove it
                    assignment_found = True
                    # Don't include this line
                    continue

            # Replace uses of the temp variable with method call
            # Pattern: word boundary + var_name + word boundary, not in assignment
            new_line = re.sub(rf"\b{self.var_name}\b", f"self.{self.var_name}()", line)
            new_method_lines.append(new_line)

        # Replace the method lines in the source
        new_lines = lines[:method_start] + new_method_lines + lines[method_end:]
        return "\n".join(new_lines)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)
            method_node = self._find_method(tree)
            if not method_node:
                return False

            assignment = self._find_assignment(method_node)
            return assignment is not None
        except (SyntaxError, ValueError):
            return False
