"""Remove Parameter refactoring - remove an unused parameter from a method signature."""

import re
from pathlib import Path
from typing import Optional
import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class RemoveParameter(RefactoringBase):
    """Remove an unused parameter from a function or method signature."""

    def __init__(self, file_path: str, target: str, parameter: str):
        """Initialize the RemoveParameter refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function/method (e.g., "function_name" or "ClassName::method_name")
            parameter: Name of the parameter to remove
        """
        self.file_path = Path(file_path)
        self.target = target
        self.parameter = parameter
        self.source = self.file_path.read_text()
        self._parse_target()

    def _parse_target(self) -> None:
        """Parse the target specification.

        Parses targets like:
        - "function_name" -> function at module level
        - "ClassName::method_name" -> method in class
        """
        if "::" in self.target:
            parts = self.target.split("::", 1)
            self.class_name = parts[0]
            self.function_name = parts[1]
        else:
            self.class_name = None
            self.function_name = self.target

    def apply(self, source: str) -> str:
        """Apply the remove parameter refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with parameter removed
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = RemoveParameterTransformer(
            class_name=self.class_name,
            function_name=self.function_name,
            parameter_name=self.parameter
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
            validator = ValidateRemoveParameterTransformer(
                class_name=self.class_name,
                function_name=self.function_name
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class RemoveParameterTransformer(cst.CSTTransformer):
    """Transform to remove a parameter from a function/method."""

    def __init__(self, class_name: Optional[str], function_name: str, parameter_name: str):
        """Initialize the transformer.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to modify
            parameter_name: Name of the parameter to remove
        """
        self.class_name = class_name
        self.function_name = function_name
        self.parameter_name = parameter_name
        self.current_class = None
        self.modified = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when entering a class."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Track when leaving a class."""
        self.current_class = None
        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Modify function definition if it matches the target."""
        # Check if this is the function we're looking for
        func_name = original_node.name.value

        if self.class_name is None:
            # Module-level function
            if self.current_class is not None:
                return updated_node
            if func_name != self.function_name:
                return updated_node
        else:
            # Class method
            if self.current_class != self.class_name:
                return updated_node
            if func_name != self.function_name:
                return updated_node

        # Found the target function, remove the parameter
        self.modified = True
        return self._remove_parameter_from_function(updated_node)

    def _remove_parameter_from_function(self, func_def: cst.FunctionDef) -> cst.FunctionDef:
        """Remove a parameter from the function signature.

        Args:
            func_def: The function definition node

        Returns:
            Modified function definition with parameter removed
        """
        params = func_def.params

        # Find and remove the parameter
        new_params_list = []
        found = False

        for param in params.params:
            if param.name.value == self.parameter_name:
                found = True
                # Skip this parameter (remove it)
            else:
                new_params_list.append(param)

        if not found:
            raise ValueError(f"Parameter '{self.parameter_name}' not found in function '{self.function_name}'")

        # Also handle kwonly_params if needed
        new_params = params.with_changes(params=tuple(new_params_list))

        return func_def.with_changes(params=new_params)


class ValidateRemoveParameterTransformer(cst.CSTVisitor):
    """Visitor to check if the target function exists."""

    def __init__(self, class_name: Optional[str], function_name: str):
        """Initialize the validator.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to find
        """
        self.class_name = class_name
        self.function_name = function_name
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
        """Check if this is the target function."""
        func_name = node.name.value

        if self.class_name is None:
            # Looking for module-level function
            if self.current_class is None and func_name == self.function_name:
                self.found = True
        else:
            # Looking for class method
            if self.current_class == self.class_name and func_name == self.function_name:
                self.found = True

        return True
