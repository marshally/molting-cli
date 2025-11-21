"""Introduce Assertion refactoring - make assumptions explicit with assertions."""

import re
from pathlib import Path
import libcst as cst
from typing import Optional

from molting.core.refactoring_base import RefactoringBase


class IntroduceAssertion(RefactoringBase):
    """Make assumptions explicit with assertions using libcst for AST transformation."""

    def __init__(self, file_path: str, target: str, condition: str, message: Optional[str] = None):
        """Initialize the IntroduceAssertion refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name#L10")
            condition: The assertion condition as a string
            message: Optional assertion message (defaults to auto-generated)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.condition = condition
        self.message = message
        self.source = self.file_path.read_text()
        # Parse the target specification to extract line number and function name
        # Parses targets like:
        # - "function_name#L10" -> function name + line number
        try:
            name_part, self.line_number, _ = self.parse_line_range_target(self.target)
        except ValueError:
            raise ValueError(f"Invalid target format: {self.target}")
        # For introduce assertion, we just use the function name (no class support)
        self.function_name = name_part

    def apply(self, source: str) -> str:
        """Apply the introduce assertion refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with assertion inserted
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = AssertionTransformer(
            function_name=self.function_name,
            line_number=self.line_number,
            condition=self.condition,
            message=self.message,
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


class AssertionTransformer(cst.CSTTransformer):
    """Transform CST to insert assertion statements."""

    def __init__(self, function_name: str, line_number: int, condition: str, message: Optional[str], source_lines: list):
        """Initialize the transformer.

        Args:
            function_name: Name of the function to modify
            line_number: Line number to insert assertion before
            condition: The assertion condition
            message: Optional assertion message
            source_lines: Original source code split by lines
        """
        self.function_name = function_name
        self.line_number = line_number
        self.condition = condition
        self.message = message
        self.source_lines = source_lines
        self.current_line = 1
        self.modified = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Visit function definitions."""
        if node.name.value == self.function_name:
            # Track that we found the function
            return True
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Process function definitions to insert assertions."""
        if updated_node.name.value != self.function_name:
            return updated_node

        # We need to insert the assertion at the beginning of the function body
        # The line_number refers to the line in the original code
        # We'll insert at the beginning of the function body (after the def line)

        new_body = self._insert_assertion_into_body(updated_node.body)
        return updated_node.with_changes(body=new_body)

    def _insert_assertion_into_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Insert assertion into function body.

        Args:
            body: The function body

        Returns:
            Modified body with assertion inserted
        """
        # Create the assertion statement
        # Parse the condition as an expression
        try:
            condition_expr = cst.parse_expression(self.condition)
        except Exception:
            # If it fails, treat it as a simple expression
            condition_expr = cst.parse_expression(self.condition)

        # Determine the message
        if self.message:
            message_str = self.message
        else:
            # Generate a default message based on the condition
            message_str = f"{self.condition.replace('not None', 'provided').replace('!= 0', 'not zero').replace('!= None', 'not None')}"

        # Create assertion with message
        assert_stmt = cst.SimpleStatementLine(
            body=[
                cst.Assert(
                    test=condition_expr,
                    msg=cst.SimpleString(f'"{message_str}"')
                )
            ]
        )

        # Get the first statement in the body
        statements = list(body.body)

        # Insert assertion before the first statement
        new_statements = [assert_stmt] + statements

        return body.with_changes(body=new_statements)
