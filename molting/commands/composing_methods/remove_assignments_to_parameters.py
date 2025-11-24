"""Remove Assignments to Parameters refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


@register_command
class RemoveAssignmentsToParametersCommand(BaseCommand):
    """Command to replace parameter reassignments with temp variables."""

    name = "remove-assignments-to-parameters"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-assignments-to-parameters refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = RemoveAssignmentsToParametersTransformer(target)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class RemoveAssignmentsToParametersTransformer(cst.CSTTransformer):
    """Transforms a function to use temp variables instead of reassigning parameters."""

    def __init__(self, function_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to refactor
        """
        self.function_name = function_name
        self.parameters_to_replace: set[str] = set()

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and add temp variable initialization."""
        if original_node.name.value != self.function_name:
            return updated_node

        # Collect parameters that are assigned to
        self.parameters_to_replace = self._find_assigned_parameters(original_node)

        if not self.parameters_to_replace:
            return updated_node

        # Get the parameter name to replace
        param_name = next(iter(self.parameters_to_replace))

        # Add result = parameter at the beginning of the function
        result_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("result"))],
                    value=cst.Name(param_name),
                )
            ]
        )

        body_transformer = ParameterReplacer(self.parameters_to_replace)
        body_with_replaced_params = cast(
            cst.IndentedBlock, updated_node.body.visit(body_transformer)
        )

        body_with_initialization = body_with_replaced_params.with_changes(
            body=(result_assignment,) + tuple(body_with_replaced_params.body)
        )

        return updated_node.with_changes(body=body_with_initialization)

    def _find_assigned_parameters(self, node: cst.FunctionDef) -> set[str]:
        """Find parameters that are assigned to in the function body.

        Args:
            node: The function definition node

        Returns:
            Set of parameter names that are assigned to
        """
        param_names = {param.name.value for param in node.params.params}

        collector = AssignmentCollector(param_names)
        node.visit(collector)

        return collector.assigned_params


class ParameterReplacer(cst.CSTTransformer):
    """Replaces parameter names with result in function body."""

    def __init__(self, parameters_to_replace: set[str]) -> None:
        """Initialize the replacer.

        Args:
            parameters_to_replace: Set of parameter names to replace
        """
        self.parameters_to_replace = parameters_to_replace

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:  # noqa: N802
        """Replace parameter references with result."""
        if updated_node.value in self.parameters_to_replace:
            return updated_node.with_changes(value="result")
        return updated_node


class AssignmentCollector(cst.CSTVisitor):
    """Collector to find assignments to parameters."""

    def __init__(self, param_names: set[str]) -> None:
        """Initialize the collector.

        Args:
            param_names: Set of parameter names to check
        """
        self.param_names = param_names
        self.assigned_params: set[str] = set()

    def visit_AugAssign(self, node: cst.AugAssign) -> None:  # noqa: N802
        """Visit augmented assignment to track parameter reassignments."""
        if isinstance(node.target, cst.Name) and node.target.value in self.param_names:
            self.assigned_params.add(node.target.value)

    def visit_Assign(self, node: cst.Assign) -> None:  # noqa: N802
        """Visit assignment to track parameter reassignments."""
        for target in node.targets:
            if isinstance(target.target, cst.Name) and target.target.value in self.param_names:
                self.assigned_params.add(target.target.value)
