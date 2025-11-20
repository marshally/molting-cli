"""Replace Nested Conditional with Guard Clauses refactoring."""

import re
from pathlib import Path
import libcst as cst
from typing import Optional, List

from molting.core.refactoring_base import RefactoringBase


class ReplaceNestedConditionalWithGuardClauses(RefactoringBase):
    """Convert nested if-else statements to guard clauses with early returns."""

    def __init__(self, file_path: str, target: str):
        """Initialize the refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name#L2")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()
        self._parse_target()

    def _parse_target(self) -> None:
        """Parse the target specification to extract function name and line number.

        Parses targets like:
        - "function_name#L2" -> function name + line number
        - "function_name#L2-L5" -> function name + range of lines (use first line)
        - "ClassName::method_name#L3" -> class name + method name + line number
        - "ClassName::method_name#L3-L7" -> class + method + line range (use first line)
        """
        # Match both single line and range formats
        pattern = r'^(.+?)#L(\d+)(?:-L\d+)?$'
        match = re.match(pattern, self.target)

        if not match:
            raise ValueError(f"Invalid target format: {self.target}")

        name_part = match.group(1)
        self.line_number = int(match.group(2))

        # Check if it's a class method (contains ::)
        if "::" in name_part:
            self.class_name, self.function_name = name_part.split("::", 1)
        else:
            self.class_name = None
            self.function_name = name_part

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with guard clauses
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ReplaceNestedConditionalTransformer(
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


class ReplaceNestedConditionalTransformer(cst.CSTTransformer):
    """Transform CST to replace nested conditionals with guard clauses."""

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
        self.inside_target_class = False
        self.found_target = False

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

        # Process the function body to find and replace nested conditionals
        new_body = self._process_function_body(updated_node.body)
        return updated_node.with_changes(body=new_body)

    def _process_function_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Process function body to replace nested conditionals with guard clauses.

        Args:
            body: The function body

        Returns:
            Modified body with guard clauses
        """
        statements = list(body.body)
        new_statements = []

        for i, stmt in enumerate(statements):
            if isinstance(stmt, cst.If) and not self.found_target:
                # We found an if statement, convert it to guard clauses
                converted_stmts = self._convert_to_guard_clauses(stmt)
                new_statements.extend(converted_stmts)
                self.found_target = True
                # Skip the original return statement that follows the if
                # The converted guard clauses handle all return paths
                remaining_stmts = statements[i + 1:]
                # Only add statements that are not simple return statements
                for remaining in remaining_stmts:
                    if not isinstance(remaining, cst.SimpleStatementLine) or not any(
                        isinstance(s, cst.Return) for s in remaining.body
                    ):
                        new_statements.append(remaining)
                break
            else:
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)

    def _convert_to_guard_clauses(self, if_stmt: cst.If) -> List[cst.BaseStatement]:
        """Convert a nested if-else structure to guard clauses.

        Args:
            if_stmt: The if statement to convert

        Returns:
            List of statements with guard clauses
        """
        guard_clauses = []
        current_if = if_stmt

        # Traverse the nested if-else structure
        while current_if is not None:
            # Get the condition and body
            condition = current_if.test
            body = current_if.body

            # Extract the return value from the body
            return_value = self._extract_return_value(body)

            # Create a guard clause (if condition, return value)
            guard = cst.If(
                test=condition,
                body=cst.IndentedBlock(
                    body=[
                        cst.SimpleStatementLine(
                            body=[cst.Return(value=return_value)]
                        )
                    ]
                )
            )
            guard_clauses.append(guard)

            # Move to the else clause
            orelse = current_if.orelse
            current_if = None

            if orelse:
                if isinstance(orelse, cst.Else):
                    # This is an else block
                    # Check if the else block contains a single if statement (elif pattern)
                    if isinstance(orelse.body, cst.IndentedBlock) and len(orelse.body.body) == 1:
                        first_stmt = orelse.body.body[0]
                        if isinstance(first_stmt, cst.If):
                            # This is an elif
                            current_if = first_stmt
                        else:
                            # Regular else block with assignment
                            return_value = self._extract_return_value(orelse.body)
                            guard_clauses.append(
                                cst.SimpleStatementLine(
                                    body=[cst.Return(value=return_value)]
                                )
                            )
                            break
                    else:
                        # Final else block
                        return_value = self._extract_return_value(orelse.body)
                        guard_clauses.append(
                            cst.SimpleStatementLine(
                                body=[cst.Return(value=return_value)]
                            )
                        )
                        break
                elif isinstance(orelse, cst.If):
                    # This shouldn't happen in our case, but handle it
                    current_if = orelse

        return guard_clauses

    def _extract_return_value(self, body: cst.BaseCompoundStatement) -> cst.BaseExpression:
        """Extract the return value from a body block.

        Args:
            body: The body block (IndentedBlock or other)

        Returns:
            The expression to return
        """
        if isinstance(body, cst.IndentedBlock):
            # Get the first statement in the block
            if body.body:
                stmt = body.body[0]
                if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                    first = stmt.body[0]
                    # Check if it's an assignment
                    if isinstance(first, cst.Assign):
                        return first.value
                    # Check if it's already a return
                    if isinstance(first, cst.Return):
                        return first.value
        return cst.Name("None")
