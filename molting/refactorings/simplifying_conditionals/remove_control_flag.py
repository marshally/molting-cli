"""Remove Control Flag refactoring - replace control flag variables with break or return statements."""

import re
from pathlib import Path
from typing import Optional

import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class RemoveControlFlag(RefactoringBase):
    """Replace control flag variables with break or return statements using libcst."""

    def __init__(self, file_path: str, target: str):
        """Initialize the RemoveControlFlag refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name::flag_name" or "ClassName::method_name::flag_name")

        Raises:
            ValueError: If target format is invalid
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()
        self._parse_target()

    def _parse_target(self) -> None:
        """Parse the target specification to extract class name, function name, and flag name.

        Parses targets like:
        - "function_name::flag_name" -> function name + flag name
        - "ClassName::method_name::flag_name" -> class name + method name + flag name

        Raises:
            ValueError: If target format is invalid
        """
        parts = self.target.split("::")

        if len(parts) == 2:
            # function_name::flag_name
            self.function_name = parts[0]
            self.flag_name = parts[1]
            self.class_name = None
        elif len(parts) == 3:
            # ClassName::method_name::flag_name
            self.class_name = parts[0]
            self.function_name = parts[1]
            self.flag_name = parts[2]
        else:
            raise ValueError(f"Invalid target format: {self.target}")

    def apply(self, source: str) -> str:
        """Apply the remove control flag refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with control flags removed

        Raises:
            ValueError: If the source code cannot be parsed or refactoring cannot be applied
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = RemoveControlFlagTransformer(
            function_name=self.function_name,
            class_name=self.class_name,
            flag_name=self.flag_name
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
        return f"def {self.function_name}" in source and self.flag_name in source


class RemoveControlFlagTransformer(cst.CSTTransformer):
    """Transform CST to remove control flag variables."""

    def __init__(self, function_name: str, class_name: Optional[str], flag_name: str):
        """Initialize the transformer.

        Args:
            function_name: Name of the function to modify
            class_name: Optional name of the class containing the function
            flag_name: Name of the control flag variable
        """
        self.function_name = function_name
        self.class_name = class_name
        self.flag_name = flag_name
        self.inside_target_class = False
        self.inside_target_function = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when we enter the target class."""
        if self.class_name and node.name.value == self.class_name:
            self.inside_target_class = True
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Track when we leave the target class."""
        if self.class_name and updated_node.name.value == self.class_name:
            self.inside_target_class = False
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Track when we enter the target function."""
        if node.name.value == self.function_name:
            # If we're looking for a class method and we're inside the right class, mark it
            if self.class_name and self.inside_target_class:
                self.inside_target_function = True
            # If we're looking for a standalone function and not inside a class, mark it
            elif not self.class_name and not self.inside_target_class:
                self.inside_target_function = True
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Process function definitions."""
        if updated_node.name.value == self.function_name:
            if (self.class_name and self.inside_target_class) or (not self.class_name and not self.inside_target_class):
                # We're leaving the target function
                self.inside_target_function = False

        return updated_node
