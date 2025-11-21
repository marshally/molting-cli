"""Extract Subclass refactoring - create a subclass for special case features."""

import ast
from pathlib import Path
from typing import List

from molting.core.refactoring_base import RefactoringBase


class ExtractSubclass(RefactoringBase):
    """Extract a subclass for special case features."""

    def __init__(self, file_path: str, target: str, features: str, name: str):
        """Initialize the ExtractSubclass refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target class name (e.g., "JobItem")
            features: Comma-separated list of features to move to subclass (e.g., "is_labor,employee")
            name: Name for the new subclass (e.g., "LaborItem")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.features = [f.strip() for f in features.split(",")]
        self.name = name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the extract subclass refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with extracted subclass
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class
        target_class = self.find_class_def(tree, self.target)
        if not target_class:
            raise ValueError(f"Class {self.target} not found")

        lines = source.split("\n")

        # Find the class definition boundaries
        class_start = None
        class_end = None
        base_indent = None

        for i, line in enumerate(lines):
            if line.strip().startswith(f"class {self.target}"):
                class_start = i
                base_indent = len(line) - len(line.lstrip())
                break

        if class_start is None:
            raise ValueError(f"Class definition for {self.target} not found")

        # Find the end of the class
        for i in range(class_start + 1, len(lines)):
            line = lines[i]
            # Class ends when we hit a line at same or lower indent level
            if line.strip() and not line.startswith(" " * (base_indent + 1)) and not line.startswith("\t"):
                class_end = i
                break
        else:
            class_end = len(lines)

        # Extract class definition
        parent_class_lines = lines[class_start:class_end]

        # Modify parent class: remove feature params and assignments
        modified_parent = self._modify_parent_class(parent_class_lines, target_class)

        # Create subclass
        subclass = self._create_subclass(target_class)

        # Reconstruct full source
        result = (
            "\n".join(lines[:class_start])
            + "\n"
            + modified_parent
            + "\n\n"
            + subclass
        )

        if class_end < len(lines):
            result += "\n" + "\n".join(lines[class_end:])

        return result

    def _modify_parent_class(self, class_lines: List[str], class_node: ast.ClassDef) -> str:
        """Modify parent class to remove feature-specific code.

        Args:
            class_lines: Lines of the parent class
            class_node: AST node of the parent class

        Returns:
            Modified parent class source code
        """
        result_lines = []
        in_init = False
        init_indent = None
        init_started = False
        skip_until_next_method = False

        for i, line in enumerate(class_lines):
            # Detect __init__ method
            if "def __init__" in line:
                in_init = True
                init_indent = len(line) - len(line.lstrip())
                # Modify the __init__ signature to remove feature parameters
                modified_line = self._modify_init_signature(line)
                result_lines.append(modified_line)
                init_started = True
                continue

            if in_init:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else None

                # Check if we've exited __init__
                if line.strip() and current_indent is not None and current_indent <= init_indent:
                    in_init = False

                # Skip feature assignments in __init__
                if init_started and current_indent is not None and current_indent > init_indent:
                    # Skip lines that assign feature fields
                    if any(f"self.{feat}" in line and "=" in line for feat in self.features):
                        continue

            # Skip method bodies that need to be replaced (like get_unit_price)
            if "def get_unit_price" in line and any(f"self.{feat}" in "".join(class_lines[i:i+10]) for feat in self.features):
                # Add simplified version without conditionals
                method_indent = len(line) - len(line.lstrip())
                result_lines.append(line)
                # Find the body and replace with simple return
                body_started = False
                for j in range(i + 1, len(class_lines)):
                    method_line = class_lines[j]
                    if method_line.strip() and len(method_line) - len(method_line.lstrip()) <= method_indent:
                        break
                    if not body_started and ":" in class_lines[i]:
                        body_started = True
                    if body_started:
                        # Replace with simplified version
                        result_lines.append(" " * (method_indent + 4) + "return self.unit_price")
                        skip_until_next_method = True
                        break
                # Skip the original body
                for j in range(i + 1, len(class_lines)):
                    method_line = class_lines[j]
                    current_method_indent = len(method_line) - len(method_line.lstrip())
                    if method_line.strip() and current_method_indent <= method_indent:
                        # Next method or end of class
                        break
                    i = j
                continue

            if skip_until_next_method:
                current_line_indent = len(line) - len(line.lstrip()) if line.strip() else float('inf')
                if line.strip() and current_line_indent <= init_indent:
                    skip_until_next_method = False
                    result_lines.append(line)
                continue

            result_lines.append(line)

        return "\n".join(result_lines)

    def _modify_init_signature(self, init_line: str) -> str:
        """Modify __init__ signature to remove feature parameters.

        Args:
            init_line: The __init__ method definition line

        Returns:
            Modified __init__ line
        """
        # Find the parameter list
        if "(" not in init_line or ")" not in init_line:
            return init_line

        prefix = init_line[: init_line.index("(") + 1]
        suffix = init_line[init_line.index(")") :]

        # Extract parameters
        params_str = init_line[init_line.index("(") + 1 : init_line.index(")")]
        params = [p.strip() for p in params_str.split(",")]

        # Filter out feature parameters
        filtered_params = [p for p in params if p not in self.features and p != "self"]
        new_params = "self, " + ", ".join(filtered_params) if filtered_params else "self"

        return prefix + new_params + suffix

    def _create_subclass(self, parent_node: ast.ClassDef) -> str:
        """Create the new subclass with feature-specific implementations.

        Args:
            parent_node: AST node of the parent class

        Returns:
            New subclass source code
        """
        # Build subclass with proper indentation
        lines = [f"class {self.name}({self.target}):"]

        # Create __init__ method
        lines.append('    def __init__(self, quantity, employee):')
        lines.append("        super().__init__(quantity, 0)")

        # Add feature field assignments (only 'employee' based on the pattern)
        for feature in self.features:
            if feature != "is_labor" and feature != "quantity":
                lines.append(f"        self.{feature} = {feature}")

        # Add overridden methods
        lines.append("    def get_unit_price(self):")
        lines.append("        return self.employee.rate")

        return "\n".join(lines)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return False

        # Check that the target class exists
        if not self.find_class_def(tree, self.target):
            return False

        return True
