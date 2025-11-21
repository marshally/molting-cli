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
        self.source = self.file_path.read_text()
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
        # TODO: Implement the actual consolidation logic
        return body
