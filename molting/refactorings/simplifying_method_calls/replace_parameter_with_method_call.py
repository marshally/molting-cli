"""Replace Parameter with Method Call refactoring - remove parameter by calling method instead."""

from pathlib import Path
from typing import Optional, Union

import libcst as cst

from molting.core.class_aware_transformer import ClassAwareTransformer
from molting.core.class_aware_validator import ClassAwareValidator
from molting.core.refactoring_base import RefactoringBase


class ReplaceParameterWithMethodCall(RefactoringBase):
    """Remove a parameter by replacing it with a method call."""

    def __init__(self, file_path: str, target: str):
        """Initialize the ReplaceParameterWithMethodCall refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target in format "ClassName::method_name::parameter_name"
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

        # Parse the target specification: "ClassName::method_name::parameter_name"
        parts = target.split("::")
        if len(parts) != 3:
            raise ValueError(
                f"Target '{target}' must be in format 'ClassName::method_name::parameter_name'"
            )

        self.class_name = parts[0]
        self.method_name = parts[1]
        self.parameter_name = parts[2]

    def apply(self, source: str) -> str:
        """Apply the replace parameter with method call refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with parameter replaced by method call
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # First pass: find the parameter index
        finder = ParameterIndexFinder(
            class_name=self.class_name,
            method_name=self.method_name,
            parameter_name=self.parameter_name,
        )
        tree.visit(finder)

        if finder.parameter_index is None:
            raise ValueError(f"Could not find target: {self.target}")

        # Second pass: apply the transformation with the known parameter index
        transformer = ReplaceParameterWithMethodCallTransformer(
            class_name=self.class_name,
            method_name=self.method_name,
            parameter_name=self.parameter_name,
            parameter_index=finder.parameter_index,
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
            validator = ValidateReplaceParameterWithMethodCallTransformer(
                class_name=self.class_name,
                method_name=self.method_name,
                parameter_name=self.parameter_name,
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class ParameterIndexFinder(cst.CSTVisitor):
    """Find the index of the parameter in the target method."""

    def __init__(self, class_name: str, method_name: str, parameter_name: str):
        """Initialize the finder.

        Args:
            class_name: Class name containing the target method
            method_name: Method name to find
            parameter_name: Parameter to find the index of
        """
        self.class_name = class_name
        self.method_name = method_name
        self.parameter_name = parameter_name
        self.parameter_index: Optional[int] = None
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track class context."""
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        """Exit class context."""
        self.current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Find the parameter index in the target method."""
        func_name = node.name.value

        # Check if this is the target method
        if self.current_class == self.class_name and func_name == self.method_name:
            # Found the target function, find the parameter index
            for i, param in enumerate(node.params.params):
                if param.name.value == self.parameter_name:
                    self.parameter_index = i
                    break

        return True


class ReplaceParameterWithMethodCallTransformer(ClassAwareTransformer):
    """Transform to replace a parameter with a method call."""

    def __init__(
        self, class_name: str, method_name: str, parameter_name: str, parameter_index: int
    ):
        """Initialize the transformer.

        Args:
            class_name: Class name containing the target method
            method_name: Method name to modify
            parameter_name: Parameter to remove
            parameter_index: Index of the parameter in the method signature
        """
        super().__init__(class_name=class_name, function_name=method_name)
        self.parameter_name = parameter_name
        self.modified = False
        self.parameter_index: Optional[int] = parameter_index
        self.should_remove_assignment = False

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> Union[cst.SimpleStatementLine, cst.RemovalSentinel]:
        """Remove assignment statements for the parameter variable."""
        # Check if this is an assignment to the parameter name
        if len(updated_node.body) == 1:
            stmt = updated_node.body[0]
            if isinstance(stmt, cst.Assign):
                # Check if the assignment target is the parameter name
                for target in stmt.targets:
                    if (
                        isinstance(target.target, cst.Name)
                        and target.target.value == self.parameter_name
                    ):
                        # This is an assignment to the parameter - remove it
                        return cst.RemovalSentinel.REMOVE

        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Update call sites to remove the argument for the replaced parameter."""
        # Check if this call is to the method we're modifying
        if isinstance(updated_node.func, cst.Attribute):
            # Method call like obj.method()
            if (
                isinstance(updated_node.func.attr, cst.Name)
                and updated_node.func.attr.value == self.function_name
            ):
                # Found a call to the target method - remove the argument at parameter_index
                # NOTE: parameter_index includes 'self', but call arguments don't
                # So we need to subtract 1 for method calls
                if self.parameter_index is not None:
                    arg_index = self.parameter_index - 1  # Subtract 1 for 'self'
                    if arg_index >= 0 and arg_index < len(updated_node.args):
                        return self._remove_argument_from_call(updated_node, arg_index)

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

        # Found the target function, now remove the parameter and replace its usage
        self.modified = True
        return self._transform_method(updated_node)

    def _remove_argument_from_call(self, call: cst.Call, arg_index: int) -> cst.Call:
        """Remove an argument from a function call.

        Args:
            call: The Call node to modify
            arg_index: Index of the argument to remove

        Returns:
            Modified call node with argument removed
        """
        args = call.args
        if arg_index >= len(args):
            return call

        # Remove the argument at arg_index
        new_args_list = []
        for i, arg in enumerate(args):
            if i != arg_index:
                new_args_list.append(arg)

        # Remove trailing comma from the last argument if it exists
        if new_args_list:
            last_arg = new_args_list[-1]
            new_args_list[-1] = last_arg.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        return call.with_changes(args=tuple(new_args_list))

    def _transform_method(self, func_def: cst.FunctionDef) -> cst.FunctionDef:
        """Remove parameter from the method and replace its usage.

        Args:
            func_def: The function definition node

        Returns:
            Modified function definition
        """
        # Find and remove the parameter
        params = func_def.params
        new_params_list = []
        found = False

        for i, param in enumerate(params.params):
            if param.name.value == self.parameter_name:
                found = True
                # Skip this parameter (remove it)
            else:
                new_params_list.append(param)

        if not found:
            raise ValueError(
                f"Parameter '{self.parameter_name}' not found in method '{self.function_name}'"
            )

        # Remove trailing comma from the last parameter if it exists
        if new_params_list:
            last_param = new_params_list[-1]
            new_params_list[-1] = last_param.with_changes(comma=cst.MaybeSentinel.DEFAULT)

        # Update the parameters
        new_params = params.with_changes(params=tuple(new_params_list))
        updated_func = func_def.with_changes(params=new_params)

        # Now replace usages of the parameter in the method body with method calls
        replacer = ParameterUsageReplacer(self.parameter_name)
        result = updated_func.visit(replacer)
        # Cast back to FunctionDef (visit can return RemovalSentinel, but we know it won't here)
        assert isinstance(result, cst.FunctionDef)
        return result


class ParameterUsageReplacer(cst.CSTTransformer):
    """Replace parameter usages with method calls."""

    def __init__(self, parameter_name: str):
        """Initialize the replacer.

        Args:
            parameter_name: Name of the parameter being replaced
        """
        self.parameter_name = parameter_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        """Replace parameter name with method call."""
        if original_node.value == self.parameter_name:
            # Replace with self.get_discount_level()
            # Convert parameter name to method name (e.g., discount_level -> get_discount_level)
            method_name = f"get_{self.parameter_name}"
            return cst.Call(
                func=cst.Attribute(
                    value=cst.Name("self"),
                    attr=cst.Name(method_name),
                )
            )
        return updated_node


class ValidateReplaceParameterWithMethodCallTransformer(ClassAwareValidator):
    """Visitor to check if the target method and parameter exist."""

    def __init__(self, class_name: str, method_name: str, parameter_name: str):
        """Initialize the validator.

        Args:
            class_name: Class name containing the target method
            method_name: Method name to find
            parameter_name: Parameter name to verify exists
        """
        super().__init__(class_name, method_name)
        self.parameter_name = parameter_name

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Check if this function matches target and has the parameter."""
        func_name = node.name.value

        # Check if this is the target method
        if self.current_class == self.class_name and func_name == self.function_name:
            # Found the target function, check if parameter exists
            for param in node.params.params:
                if param.name.value == self.parameter_name:
                    self.found = True
                    break

        return True
