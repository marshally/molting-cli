"""Add Parameter refactoring - add a new parameter to a method signature."""

import re
from pathlib import Path
from typing import Optional
import libcst as cst

from molting.core.refactoring_base import RefactoringBase
from molting.core.class_aware_transformer import ClassAwareTransformer


class AddParameter(RefactoringBase):
    """Add a new parameter to a function or method signature."""

    def __init__(self, file_path: str, target: str, name: str, default: Optional[str] = None):
        """Initialize the AddParameter refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function/method (e.g., "function_name" or "ClassName::method_name")
            name: Name of the new parameter
            default: Optional default value for the new parameter
        """
        self.file_path = Path(file_path)
        self.target = target
        self.name = name
        self.default = default
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
        """Apply the add parameter refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new parameter added
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = AddParameterTransformer(
            class_name=self.class_name,
            function_name=self.function_name,
            param_name=self.name,
            param_default=self.default
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
            validator = ValidateAddParameterTransformer(
                class_name=self.class_name,
                function_name=self.function_name
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class AddParameterTransformer(ClassAwareTransformer):
    """Transform to add a parameter to a function/method."""

    def __init__(self, class_name: Optional[str], function_name: str, param_name: str, param_default: Optional[str]):
        """Initialize the transformer.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to modify
            param_name: Name of the new parameter to add
            param_default: Optional default value for the parameter
        """
        super().__init__(class_name=class_name, function_name=function_name)
        self.param_name = param_name
        self.param_default = param_default
        self.modified = False

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Modify function definition if it matches the target."""
        # Check if this is the function we're looking for
        func_name = original_node.name.value

        # Check if this function matches the target
        if not self.matches_target() or func_name != self.function_name:
            return updated_node

        # Found the target function, add the parameter
        self.modified = True
        return self._add_parameter_to_function(updated_node)

    def _add_parameter_to_function(self, func_def: cst.FunctionDef) -> cst.FunctionDef:
        """Add a parameter to the function signature.

        Args:
            func_def: The function definition node

        Returns:
            Modified function definition with new parameter added
        """
        params = func_def.params

        # Create the new parameter
        if self.param_default is not None:
            # Parameter with default value
            default_value = self._create_default_value(self.param_default)
            new_param = cst.Param(
                name=cst.Name(self.param_name),
                equal=cst.AssignEqual(
                    whitespace_before=cst.SimpleWhitespace(""),
                    whitespace_after=cst.SimpleWhitespace("")
                ),
                default=default_value
            )
        else:
            # Parameter without default value
            new_param = cst.Param(name=cst.Name(self.param_name))

        # Add the parameter to the params
        new_params = params.with_changes(
            params=(*params.params, new_param)
        )

        return func_def.with_changes(params=new_params)

    def _create_default_value(self, value: str) -> cst.BaseExpression:
        """Create a CST node for the default value.

        Args:
            value: The default value as a string

        Returns:
            CST expression node
        """
        # Try to parse as a Python literal
        try:
            # Check if it's a float
            if '.' in value and self._is_all_numeric(value):
                float(value)
                return cst.Float(value)
            # Check if it's an integer
            elif value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                int(value)
                return cst.Integer(value)
        except ValueError:
            pass

        # Check if it's a known constant or looks like a Python construct
        if value in ('None', 'True', 'False'):
            try:
                parsed = cst.parse_expression(value)
                return parsed
            except Exception:
                pass

        # Fall back to treating it as a string literal
        return cst.SimpleString(f'"{value}"')

    def _is_all_numeric(self, value: str) -> bool:
        """Check if a string contains only numeric characters and a decimal point."""
        return all(c.isdigit() or c == '.' for c in value)


class ValidateAddParameterTransformer(cst.CSTVisitor):
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
