"""Consolidate Duplicate Conditional Fragments refactoring - move duplicate code outside conditionals."""

import re
from pathlib import Path
import libcst as cst
from typing import Optional, Tuple, List, Set

from molting.core.refactoring_base import RefactoringBase


class ConsolidateDuplicateConditionalFragments(RefactoringBase):
    """Move identical code appearing in all branches of a conditional outside the conditional."""

    def __init__(self, file_path: str, target: str):
        """Initialize the ConsolidateDuplicateConditionalFragments refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name#L2")
        """
        self.file_path = Path(file_path)
        self.target = target
        # Only read the file if it exists (for testing purposes)
        if self.file_path.exists():
            self.source = self.file_path.read_text()
        else:
            self.source = ""
        # Parse the target specification to extract line number and function name
        # Parses targets like:
        # - "function_name#L2" -> function name + line number
        # - "ClassName::method_name#L3" -> class name + method name + line number
        try:
            name_part, self.line_number, _ = self.parse_line_range_target(self.target)
        except ValueError:
            raise ValueError(f"Invalid target format: {self.target}")

        # Check if it's a class method (contains ::)
        if "::" in name_part:
            self.class_name, self.function_name = self.parse_qualified_target(name_part)
        else:
            self.class_name = None
            self.function_name = name_part

    def apply(self, source: str) -> str:
        """Apply the consolidate duplicate conditional fragments refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with consolidated duplicate fragments
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ConsolidateDuplicateFragmentsTransformer(
            function_name=self.function_name,
            class_name=self.class_name,
            line_number=self.line_number,
            source_lines=source.split('\n')
        )
        modified_tree = tree.visit(transformer)

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        # Check that the function exists
        return f"def {self.function_name}" in source


class ConsolidateDuplicateFragmentsTransformer(cst.CSTTransformer):
    """Transform CST to consolidate duplicate conditional fragments."""

    def __init__(self, function_name: str, class_name: Optional[str], line_number: int, source_lines: list):
        """Initialize the transformer.

        Args:
            function_name: Name of the function to modify
            class_name: Optional name of the class containing the function
            line_number: Line number of the if statement
            source_lines: Original source code split by lines
        """
        self.function_name = function_name
        self.class_name = class_name
        self.line_number = line_number
        self.source_lines = source_lines
        self.found_target = False
        self.inside_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when we enter the target class."""
        if self.class_name and node.name.value == self.class_name:
            self.inside_target_class = True
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Process the class definition."""
        if self.class_name and updated_node.name.value == self.class_name:
            self.inside_target_class = False
        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Process function definitions."""
        if updated_node.name.value != self.function_name:
            return updated_node

        # If we're looking for a class method and we're not inside the right class, skip
        if self.class_name and not self.inside_target_class:
            return updated_node

        # If we're looking for a standalone function and there's a class name, skip
        if not self.class_name and self.inside_target_class:
            return updated_node

        # Process the function body to consolidate duplicate fragments
        new_body = self._process_function_body(updated_node.body)
        return updated_node.with_changes(body=new_body)

    def _process_function_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Process function body to consolidate duplicate fragments.

        Args:
            body: The function body

        Returns:
            Modified body with consolidated duplicate fragments
        """
        statements = list(body.body)
        new_statements = []

        for stmt in statements:
            if isinstance(stmt, cst.If):
                # Try to consolidate duplicate fragments
                consolidated = self._consolidate_if_statement(stmt)
                if consolidated:
                    new_statements.extend(consolidated)
                else:
                    new_statements.append(stmt)
            else:
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)

    def _consolidate_if_statement(self, if_stmt: cst.If) -> Optional[List[cst.BaseStatement]]:
        """Consolidate duplicate fragments in an if statement.

        Args:
            if_stmt: The if statement to process

        Returns:
            List of statements with duplicates consolidated, or None if no consolidation
        """
        # Get all branches (if and else, no elif support for now)
        if not if_stmt.orelse or not isinstance(if_stmt.orelse, cst.Else):
            return None

        if_body = self._get_body_statements(if_stmt.body)
        else_body = self._get_body_statements(if_stmt.orelse.body)

        if not if_body or not else_body:
            return None

        # Check for duplicates at the end
        duplicates_at_end = self._find_duplicates_at_end(if_body, else_body)
        if duplicates_at_end:
            return self._consolidate_duplicates_at_end(if_stmt, duplicates_at_end)

        # Check for duplicates at the start
        duplicates_at_start = self._find_duplicates_at_start(if_body, else_body)
        if duplicates_at_start:
            return self._consolidate_duplicates_at_start(if_stmt, duplicates_at_start)

        return None

    def _get_body_statements(self, body: cst.BaseCompoundStatement) -> List[cst.BaseStatement]:
        """Extract statements from a body.

        Args:
            body: The body to extract statements from

        Returns:
            List of statements
        """
        if isinstance(body, cst.IndentedBlock):
            return list(body.body)
        return []

    def _find_duplicates_at_end(self, if_body: List[cst.BaseStatement], else_body: List[cst.BaseStatement]) -> List[cst.BaseStatement]:
        """Find duplicate statements at the end of both branches.

        Args:
            if_body: Statements in the if branch
            else_body: Statements in the else branch

        Returns:
            List of duplicate statements at the end
        """
        duplicates = []
        min_len = min(len(if_body), len(else_body))

        # Check from the end backwards
        for i in range(1, min_len + 1):
            if_stmt = if_body[-i]
            else_stmt = else_body[-i]

            if self._statements_equal(if_stmt, else_stmt):
                duplicates.insert(0, if_stmt)
            else:
                break

        return duplicates

    def _find_duplicates_at_start(self, if_body: List[cst.BaseStatement], else_body: List[cst.BaseStatement]) -> List[cst.BaseStatement]:
        """Find duplicate statements at the start of both branches.

        Args:
            if_body: Statements in the if branch
            else_body: Statements in the else branch

        Returns:
            List of duplicate statements at the start
        """
        duplicates = []
        min_len = min(len(if_body), len(else_body))

        # Check from the start
        for i in range(min_len):
            if_stmt = if_body[i]
            else_stmt = else_body[i]

            if self._statements_equal(if_stmt, else_stmt):
                duplicates.append(if_stmt)
            else:
                break

        return duplicates

    def _statements_equal(self, stmt1: cst.BaseStatement, stmt2: cst.BaseStatement) -> bool:
        """Check if two statements are equal.

        Args:
            stmt1: First statement
            stmt2: Second statement

        Returns:
            True if statements are equal
        """
        return stmt1.deep_equals(stmt2)

    def _consolidate_duplicates_at_end(self, if_stmt: cst.If, duplicates: List[cst.BaseStatement]) -> List[cst.BaseStatement]:
        """Move duplicate statements from the end of branches to after the if-else.

        Args:
            if_stmt: The if statement
            duplicates: List of duplicate statements

        Returns:
            List of statements with duplicates moved after the if-else
        """
        if_body = self._get_body_statements(if_stmt.body)
        else_body = self._get_body_statements(if_stmt.orelse.body)

        # Remove duplicates from the end of each branch
        num_duplicates = len(duplicates)
        new_if_body = if_body[:-num_duplicates] if num_duplicates > 0 else if_body
        new_else_body = else_body[:-num_duplicates] if num_duplicates > 0 else else_body

        # Create new if statement with shortened branches
        new_if_stmt = if_stmt.with_changes(
            body=cst.IndentedBlock(body=new_if_body),
            orelse=cst.Else(body=cst.IndentedBlock(body=new_else_body))
        )

        # Return the modified if statement followed by the duplicate statements
        return [new_if_stmt] + duplicates

    def _consolidate_duplicates_at_start(self, if_stmt: cst.If, duplicates: List[cst.BaseStatement]) -> List[cst.BaseStatement]:
        """Move duplicate statements from the start of branches to before the if-else.

        Args:
            if_stmt: The if statement
            duplicates: List of duplicate statements

        Returns:
            List of statements with duplicates moved before the if-else
        """
        if_body = self._get_body_statements(if_stmt.body)
        else_body = self._get_body_statements(if_stmt.orelse.body)

        # Remove duplicates from the start of each branch
        num_duplicates = len(duplicates)
        new_if_body = if_body[num_duplicates:]
        new_else_body = else_body[num_duplicates:]

        # Create new if statement with shortened branches
        new_if_stmt = if_stmt.with_changes(
            body=cst.IndentedBlock(body=new_if_body),
            orelse=cst.Else(body=cst.IndentedBlock(body=new_else_body))
        )

        # Return the duplicate statements followed by the modified if statement
        return duplicates + [new_if_stmt]
