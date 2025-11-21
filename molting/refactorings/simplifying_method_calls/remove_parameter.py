"""Remove Parameter refactoring - remove an unused parameter from a method signature."""

from pathlib import Path
from typing import Optional

import libcst as cst

from molting.core.class_aware_transformer import ClassAwareTransformer
from molting.core.class_aware_validator import ClassAwareValidator
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
        # Parse the target specification - if it contains "::" it's "ClassName::method_name"
        # otherwise it's just "function_name"
        self.class_name: Optional[str]
        self.function_name: str
        if "::" in self.target:
            self.class_name, self.function_name = self.parse_qualified_target(self.target)
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
            parameter_name=self.parameter,
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
                class_name=self.class_name, function_name=self.function_name
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class RemoveParameterTransformer(ClassAwareTransformer):
    """Transform to remove a parameter from a function/method."""

    def __init__(self, class_name: Optional[str], function_name: str, parameter_name: str):
        """Initialize the transformer.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to modify
            parameter_name: Name of the parameter to remove
        """
        super().__init__(class_name=class_name, function_name=function_name)
        self.parameter_name = parameter_name
        self.modified = False
        self.parameter_index: Optional[
            int
        ] = None  # Will be set when we find and modify the function

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Update call sites to remove the argument corresponding to the removed parameter."""
        # Only update calls if we've identified the parameter to remove
        if self.parameter_index is None:
            return updated_node

        # Check if this call is to the function we're modifying
        if isinstance(updated_node.func, cst.Name):
            # Direct function call
            func_name = updated_node.func.value
            if func_name == self.function_name and self.class_name is None:
                return self._remove_argument_from_call(updated_node)
        elif isinstance(updated_node.func, cst.Attribute):
            # Method call like obj.method()
            if (
                isinstance(updated_node.func.attr, cst.Name)
                and updated_node.func.attr.value == self.function_name
            ):
                return self._remove_argument_from_call(updated_node)

        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Modify function definition if it matches the target."""
        # Check if this is the function we're looking for
        func_name = original_node.name.value

        # Check if this function matches the target
        if not self.matches_target() or func_name != self.function_name:
            return updated_node

        # Found the target function, remove the parameter
        self.modified = True
        return self._remove_parameter_from_function(updated_node)

    def _remove_argument_from_call(self, call: cst.Call) -> cst.Call:
        """Remove an argument from a function call.

        Args:
            call: The Call node to modify

        Returns:
            Modified call node with argument removed
        """
        args = call.args
        if self.parameter_index is None or self.parameter_index >= len(args):
            return call

        # Remove the argument at parameter_index
        new_args_list = []
        for i, arg in enumerate(args):
            if i != self.parameter_index:
                new_args_list.append(arg)

        # Remove trailing comma from the last argument if it exists
        if new_args_list:
            last_arg = new_args_list[-1]
            new_args_list[-1] = last_arg.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        return call.with_changes(args=tuple(new_args_list))

    def _remove_parameter_from_function(self, func_def: cst.FunctionDef) -> cst.FunctionDef:
        """Remove a parameter from the function signature.

        Args:
            func_def: The function definition node

        Returns:
            Modified function definition with parameter removed
        """
        params = func_def.params

        # Find and remove the parameter, tracking its index
        new_params_list = []
        found = False
        self.parameter_index = None

        for i, param in enumerate(params.params):
            if param.name.value == self.parameter_name:
                found = True
                self.parameter_index = i
                # Skip this parameter (remove it)
            else:
                new_params_list.append(param)

        if not found:
            raise ValueError(
                f"Parameter '{self.parameter_name}' not found in function '{self.function_name}'"
            )

        # Remove trailing comma from the last parameter if it exists
        if new_params_list:
            last_param = new_params_list[-1]
            new_params_list[-1] = last_param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        # Also handle kwonly_params if needed
        new_params = params.with_changes(params=tuple(new_params_list))

        return func_def.with_changes(params=new_params)


class ValidateRemoveParameterTransformer(ClassAwareValidator):
    """Visitor to check if the target function exists."""

    def __init__(self, class_name: Optional[str], function_name: str):
        """Initialize the validator.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to find
        """
        super().__init__(class_name, function_name)
