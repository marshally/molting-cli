"""Remove Assignments to Parameters refactoring using libcst."""

from pathlib import Path
import libcst as cst
from typing import Sequence

from molting.core.refactoring_base import RefactoringBase


class RemoveAssignmentsToParameters(RefactoringBase):
    """Remove assignments to parameters by replacing with local variables.

    From Martin Fowler's catalog: "The code assigns to a parameter.
    Use a temporary variable instead."
    """

    def __init__(self, file_path: str, target: str):
        """Initialize the Remove Assignments to Parameters refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function/method name (e.g., "discount" or "ClassName::method_name")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code
        """
        self.source = source

        # Parse the target to extract function/method name and class name if present
        func_name = self.target.split("::")[-1]

        # Parse the source code into a CST
        module = cst.parse_module(source)

        # Transform the module
        transformer = ParameterAssignmentTransformer(func_name)
        modified_tree = module.visit(transformer)

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            cst.parse_module(source)
            return True
        except Exception:
            return False


class ParameterAssignmentTransformer(cst.CSTTransformer):
    """Transform functions to remove parameter assignments."""

    def __init__(self, target_func_name: str):
        """Initialize with the target function name.

        Args:
            target_func_name: Name of the function to refactor
        """
        self.target_func_name = target_func_name
        self.param_names = set()  # Will be populated when we visit the function

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Process the target function to remove parameter assignments."""
        if original_node.name.value == self.target_func_name:
            # Get the parameter names
            params = original_node.params
            self.param_names = self._extract_param_names(params)

            # Process the function body
            new_body = self._process_function_body(original_node, updated_node)
            return updated_node.with_changes(body=new_body)

        return updated_node

    def _extract_param_names(self, params: cst.Parameters) -> set:
        """Extract parameter names from function parameters."""
        param_names = set()

        # Regular parameters
        for param in params.params:
            param_names.add(param.name.value)

        # Star arg (*args)
        if params.star_arg:
            if isinstance(params.star_arg, cst.Param):
                param_names.add(params.star_arg.name.value)

        # Keyword-only parameters
        if params.kwonly_params:
            for param in params.kwonly_params:
                param_names.add(param.name.value)

        # Star kwarg (**kwargs)
        if params.star_kwarg:
            if isinstance(params.star_kwarg, cst.Param):
                param_names.add(params.star_kwarg.name.value)

        return param_names

    def _process_function_body(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.IndentedBlock:
        """Process the function body to remove parameter assignments."""
        body = updated_node.body

        if not isinstance(body, cst.IndentedBlock):
            return body

        # First pass: identify which parameters are assigned
        param_assignments = {}
        for stmt in body.body:
            self._find_param_assignments(stmt, param_assignments)

        # If no parameter assignments found, return unchanged
        if not param_assignments:
            return body

        # Determine which parameter to replace (first one assigned)
        param_to_replace = list(param_assignments.keys())[0]
        temp_var_name = "result"

        # Add initialization statement at the beginning
        init_stmt = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(temp_var_name))],
                    value=cst.Name(param_to_replace)
                )
            ]
        )

        # Replace parameter usages with temp variable in the body
        replacer = ParameterUsageReplacer(param_to_replace, temp_var_name)
        new_body_stmts = []
        for stmt in body.body:
            new_stmt = stmt.visit(replacer)
            new_body_stmts.append(new_stmt)

        # Combine init statement with transformed body
        all_statements = [init_stmt] + new_body_stmts
        return body.with_changes(body=all_statements)

    def _find_param_assignments(self, node: cst.CSTNode, param_assignments: dict):
        """Find assignments to parameters in the code."""
        if isinstance(node, cst.SimpleStatementLine):
            for stmt in node.body:
                if isinstance(stmt, (cst.Assign, cst.AugAssign)):
                    target = stmt.targets[0].target if isinstance(stmt, cst.Assign) else stmt.target
                    if isinstance(target, cst.Name):
                        if target.value in self.param_names:
                            param_assignments[target.value] = True

        elif isinstance(node, cst.IndentedBlock):
            for stmt in node.body:
                self._find_param_assignments(stmt, param_assignments)

        elif isinstance(node, cst.If):
            for stmt in node.body.body:
                self._find_param_assignments(stmt, param_assignments)
            if node.orelse:
                if isinstance(node.orelse, cst.IndentedBlock):
                    for stmt in node.orelse.body:
                        self._find_param_assignments(stmt, param_assignments)
                elif isinstance(node.orelse, cst.If):
                    self._find_param_assignments(node.orelse, param_assignments)


class ParameterUsageReplacer(cst.CSTTransformer):
    """Replace parameter usages with temporary variable."""

    def __init__(self, param_name: str, temp_var_name: str):
        """Initialize the replacer.

        Args:
            param_name: Name of the parameter to replace
            temp_var_name: Name of the temporary variable
        """
        self.param_name = param_name
        self.temp_var_name = temp_var_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        """Replace parameter names with temp variable in all contexts."""
        if original_node.value == self.param_name:
            return updated_node.with_changes(value=self.temp_var_name)
        return updated_node

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        """Handle assignments to replace parameter assignments with temp var assignments."""
        target = original_node.targets[0].target

        # Check if assigning to the parameter
        if isinstance(target, cst.Name) and target.value == self.param_name:
            # Replace the target with the temp variable
            return updated_node.with_changes(
                targets=[cst.AssignTarget(target=cst.Name(self.temp_var_name))]
            )

        return updated_node

    def leave_AugAssign(self, original_node: cst.AugAssign, updated_node: cst.AugAssign) -> cst.AugAssign:
        """Handle augmented assignments (+=, -=, etc.) to the parameter."""
        target = original_node.target

        # Check if assigning to the parameter
        if isinstance(target, cst.Name) and target.value == self.param_name:
            # Replace the target with the temp variable
            return updated_node.with_changes(target=cst.Name(self.temp_var_name))

        return updated_node
