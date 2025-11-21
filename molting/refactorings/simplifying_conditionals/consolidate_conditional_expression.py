"""Consolidate Conditional Expression refactoring - combine conditions with same result."""

import re
from pathlib import Path
import libcst as cst
from typing import Optional, Tuple, List, Set

from molting.core.refactoring_base import RefactoringBase


class ConsolidateConditionalExpression(RefactoringBase):
    """Combine a sequence of conditional checks with the same result into a single conditional."""

    def __init__(self, file_path: str, target: str):
        """Initialize the ConsolidateConditionalExpression refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name#L2-L7")
        """
        self.file_path = Path(file_path)
        self.target = target
        # Parse the target specification to extract function name and line range.
        # Parses targets like:
        # - "function_name#L2-L7" -> function name + line range
        # - "ClassName::method_name#L3-L10" -> class name + method name + line range
        try:
            name_part, self.start_line, self.end_line = self.parse_line_range_target(self.target)
        except ValueError:
            raise ValueError(f"Invalid target format: {self.target}")

        # Check if it's a class method (contains ::)
        if "::" in name_part:
            self.class_name, self.function_name = self.parse_qualified_target(name_part)
        else:
            self.class_name = None
            self.function_name = name_part

        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the consolidate conditional expression refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with consolidated conditionals
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ConsolidateConditionalTransformer(
            function_name=self.function_name,
            class_name=self.class_name,
            start_line=self.start_line,
            end_line=self.end_line,
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


class ConsolidateConditionalTransformer(cst.CSTTransformer):
    """Transform CST to consolidate conditional expressions."""

    def __init__(self, function_name: str, class_name: Optional[str], start_line: int, end_line: int, source_lines: list):
        """Initialize the transformer.

        Args:
            function_name: Name of the function to modify
            class_name: Optional name of the class containing the function
            start_line: Starting line number of the range
            end_line: Ending line number of the range
            source_lines: Original source code split by lines
        """
        self.function_name = function_name
        self.class_name = class_name
        self.start_line = start_line
        self.end_line = end_line
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

        # Process the function body to consolidate conditionals
        new_body = self._process_function_body(updated_node.body)
        return updated_node.with_changes(body=new_body)

    def _process_function_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Process function body to consolidate conditionals.

        Args:
            body: The function body

        Returns:
            Modified body with consolidated conditionals
        """
        statements = list(body.body)
        new_statements = []
        i = 0

        while i < len(statements):
            stmt = statements[i]
            
            # Check if this is an if statement in our target range
            if isinstance(stmt, cst.If):
                # Collect all consecutive if statements with same body
                consolidated = self._try_consolidate_ifs(statements, i)
                
                if consolidated:
                    new_statements.append(consolidated['statement'])
                    i += consolidated['count']
                else:
                    new_statements.append(stmt)
                    i += 1
            else:
                new_statements.append(stmt)
                i += 1

        return body.with_changes(body=new_statements)

    def _try_consolidate_ifs(self, statements: list, start_index: int) -> Optional[dict]:
        """Try to consolidate consecutive if statements with the same body.

        Args:
            statements: List of statements
            start_index: Index of the first if statement

        Returns:
            Dictionary with 'statement' and 'count' if consolidation successful, None otherwise
        """
        if not isinstance(statements[start_index], cst.If):
            return None

        # Collect all consecutive if statements with the same body
        if_statements = []
        i = start_index

        while i < len(statements) and isinstance(statements[i], cst.If):
            if_stmt = statements[i]
            
            # Only process if statements without else clauses
            if if_stmt.orelse is None:
                if_statements.append(if_stmt)
                i += 1
            else:
                break

        # Need at least 2 if statements to consolidate
        if len(if_statements) < 2:
            return None

        # Check if all have the same body
        first_body = if_statements[0].body
        all_same_body = all(
            self._bodies_equal(if_stmt.body, first_body)
            for if_stmt in if_statements[1:]
        )

        if not all_same_body:
            return None

        # Consolidate the conditions with OR logic
        conditions = [if_stmt.test for if_stmt in if_statements]
        consolidated_condition = self._combine_conditions_with_or(conditions)

        # Create the consolidated if statement
        consolidated_if = if_statements[0].with_changes(test=consolidated_condition)

        return {
            'statement': consolidated_if,
            'count': len(if_statements)
        }

    def _bodies_equal(self, body1: cst.BaseCompoundStatement, body2: cst.BaseCompoundStatement) -> bool:
        """Check if two statement bodies are equal.

        Args:
            body1: First body
            body2: Second body

        Returns:
            True if bodies are equal, False otherwise
        """
        return body1.deep_equals(body2)

    def _combine_conditions_with_or(self, conditions: List[cst.BaseExpression]) -> cst.BaseExpression:
        """Combine multiple conditions with OR logic.

        Args:
            conditions: List of condition expressions

        Returns:
            Combined condition using OR operators
        """
        if not conditions:
            raise ValueError("No conditions to combine")

        if len(conditions) == 1:
            return conditions[0]

        # Build OR chain: condition1 or condition2 or condition3
        result = conditions[0]
        for condition in conditions[1:]:
            result = cst.BooleanOperation(
                operator=cst.Or(),
                left=result,
                right=condition
            )

        return result
