"""Hide Method refactoring - make a public method private by adding underscore prefix."""

from pathlib import Path
from typing import Optional
import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class HideMethod(RefactoringBase):
    """Hide a public method by renaming it to start with underscore."""

    def __init__(self, file_path: str, target: str):
        """Initialize the HideMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method (e.g., "ClassName::method_name")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()
        self._parse_target()

    def _parse_target(self) -> None:
        """Parse the target specification.

        Parses targets like:
        - "ClassName::method_name" -> method in class
        """
        if "::" not in self.target:
            raise ValueError(f"Invalid target format: {self.target}. Expected 'ClassName::method_name'")

        parts = self.target.split("::", 1)
        self.class_name = parts[0]
        self.method_name = parts[1]

    def apply(self, source: str) -> str:
        """Apply the hide method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with method hidden
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = HideMethodTransformer(
            class_name=self.class_name,
            method_name=self.method_name
        )
        modified_tree = tree.visit(transformer)

        if not transformer.modified:
            raise ValueError(f"Could not find target: {self.target}")

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = cst.parse_module(source)
            validator = ValidateHideMethodTransformer(
                class_name=self.class_name,
                method_name=self.method_name
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class HideMethodTransformer(cst.CSTTransformer):
    """Transform to hide a method by adding underscore prefix."""

    def __init__(self, class_name: str, method_name: str):
        """Initialize the transformer.

        Args:
            class_name: Class name containing the method
            method_name: Method name to hide
        """
        self.class_name = class_name
        self.method_name = method_name
        self.current_class = None
        self.modified = False
        self.new_method_name = f"_{method_name}"

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when entering a class."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Track when leaving a class."""
        if self.current_class == self.class_name:
            self.current_class = None
        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Rename method if it matches the target."""
        # Check if this is the method we're looking for
        if self.current_class != self.class_name:
            return updated_node

        if original_node.name.value != self.method_name:
            return updated_node

        # Found the target method, rename it with underscore prefix
        self.modified = True
        return updated_node.with_changes(
            name=cst.Name(self.new_method_name)
        )

    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.Attribute:
        """Update method calls within the same class."""
        # Check if this is a self.method_name call
        if isinstance(updated_node.attr, cst.Name) and updated_node.attr.value == self.method_name:
            if isinstance(updated_node.value, cst.Name) and updated_node.value.value == "self":
                if self.current_class == self.class_name:
                    # Update the attribute name
                    return updated_node.with_changes(
                        attr=cst.Name(self.new_method_name)
                    )

        return updated_node


class ValidateHideMethodTransformer(cst.CSTVisitor):
    """Visitor to check if the target method exists."""

    def __init__(self, class_name: str, method_name: str):
        """Initialize the validator.

        Args:
            class_name: Class name containing the method
            method_name: Method name to find
        """
        self.class_name = class_name
        self.method_name = method_name
        self.found = False
        self.current_class = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when entering a class."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        """Track when leaving a class."""
        self.current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Check if this is the target method."""
        if self.current_class == self.class_name and node.name.value == self.method_name:
            self.found = True
        return True
