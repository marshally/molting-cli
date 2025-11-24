"""Inline Temp refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


@register_command
class InlineTempCommand(BaseCommand):
    """Command to inline a temporary variable by replacing uses with its expression."""

    name = "inline-temp"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply inline-temp refactoring using libCST.

        Raises:
            ValueError: If function or variable not found
        """
        target = self.params["target"]

        # Parse target format: "function_name::variable_name"
        function_name, variable_name = parse_target(target, expected_parts=2)

        # Read file
        source_code = self.file_path.read_text()

        # First pass: capture the variable expression
        module = cst.parse_module(source_code)
        collector = TempVariableCollector(function_name, variable_name)
        module.visit(collector)

        if collector.variable_expression is None:
            raise ValueError(
                f"Variable '{variable_name}' not found in function '{function_name}' "
                "or does not have a simple assignment"
            )

        # Second pass: inline the variable with metadata
        wrapper = cst.MetadataWrapper(module)
        transformer = InlineTempTransformer(
            function_name, variable_name, collector.variable_expression
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class TempVariableCollector(cst.CSTVisitor):
    """Collector to capture the temp variable expression."""

    def __init__(self, function_name: str, variable_name: str) -> None:
        """Initialize the collector.

        Args:
            function_name: Name of the function containing the variable
            variable_name: Name of the temp variable to inline
        """
        self.function_name = function_name
        self.variable_name = variable_name
        self.variable_expression: cst.BaseExpression | None = None
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to track if we're in the target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Leave function definition."""
        if node.name.value == self.function_name:
            self.in_target_function = False

    def visit_Assign(self, node: cst.Assign) -> None:  # noqa: N802
        """Visit assignment to capture the temp variable expression."""
        if not self.in_target_function:
            return

        if self._assigns_to_variable(node):
            self.variable_expression = node.value

    def _assigns_to_variable(self, assign: cst.Assign) -> bool:
        """Check if an assignment assigns to the target variable.

        Args:
            assign: The assignment node to check

        Returns:
            True if the assignment assigns to the target variable, False otherwise
        """
        for target in assign.targets:
            if isinstance(target.target, cst.Name) and target.target.value == self.variable_name:
                return True
        return False


class InlineTempTransformer(cst.CSTTransformer):
    """Transforms a function by inlining a temp variable."""

    METADATA_DEPENDENCIES = (cst.metadata.ParentNodeProvider,)

    def __init__(
        self, function_name: str, variable_name: str, variable_expression: cst.BaseExpression
    ) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function containing the variable
            variable_name: Name of the temp variable to inline
            variable_expression: The variable's expression to inline
        """
        self.function_name = function_name
        self.variable_name = variable_name
        self.variable_expression = variable_expression
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to track if we're in the target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and remove the temp variable assignment."""
        if original_node.name.value == self.function_name:
            self.in_target_function = False

            # Remove the temp variable assignment
            statements_without_temp = [
                stmt for stmt in updated_node.body.body if not self._is_temp_assignment(stmt)
            ]

            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=tuple(statements_without_temp))
            )
        return updated_node

    def leave_Name(  # noqa: N802
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        """Leave name node and replace temp variable uses with its expression."""
        if (
            self.in_target_function
            and updated_node.value == self.variable_name
            and not self._is_in_assignment_target(original_node)
        ):
            return self.variable_expression
        return updated_node

    def _is_temp_assignment(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is the temp variable assignment.

        Args:
            stmt: The statement to check

        Returns:
            True if this is the temp variable assignment, False otherwise
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        if len(stmt.body) != 1:
            return False

        if not isinstance(stmt.body[0], cst.Assign):
            return False

        return self._assigns_to_variable(stmt.body[0])

    def _assigns_to_variable(self, assign: cst.Assign) -> bool:
        """Check if an assignment assigns to the target variable.

        Args:
            assign: The assignment node to check

        Returns:
            True if the assignment assigns to the target variable, False otherwise
        """
        for target in assign.targets:
            if isinstance(target.target, cst.Name) and target.target.value == self.variable_name:
                return True
        return False

    def _is_in_assignment_target(self, node: cst.Name) -> bool:
        """Check if a name node is in an assignment target position.

        Args:
            node: The name node to check

        Returns:
            True if the name is being assigned to, False otherwise
        """
        # Walk up the parent chain to check if we're in an AssignTarget
        try:
            parent = self.get_metadata(cst.metadata.ParentNodeProvider, node)
            while parent:
                if isinstance(parent, cst.AssignTarget):
                    return True
                if isinstance(parent, cst.FunctionDef):
                    # Stop at function boundary
                    break
                parent = self.get_metadata(cst.metadata.ParentNodeProvider, parent)
        except KeyError:
            # Metadata not available, fall back to simple check
            pass
        return False
