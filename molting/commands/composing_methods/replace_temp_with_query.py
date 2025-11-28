"""Replace Temp with Query refactoring command."""

import libcst as cst
import libcst.metadata as metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.visitors import MethodConflictChecker


@register_command
class ReplaceTempWithQueryCommand(BaseCommand):
    """Command to replace a temporary variable with a query method."""

    name = "replace-temp-with-query"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-temp-with-query refactoring using libCST.

        Raises:
            ValueError: If class, method, or variable not found
        """
        target = self.params["target"]

        # Parse target format: "ClassName::method_name::variable_name"
        class_name, method_name, variable_name = parse_target(target, expected_parts=3)

        # Read file
        source_code = self.file_path.read_text()

        # First pass: capture the variable expression
        module = cst.parse_module(source_code)
        collector = TempVariableCollector(class_name, method_name, variable_name)
        module.visit(collector)

        if collector.variable_expression is None:
            raise ValueError(
                f"Variable '{variable_name}' not found in method '{class_name}::{method_name}' "
                "or does not have a simple assignment"
            )

        # Check for name conflicts - method name should not already exist
        conflict_checker = MethodConflictChecker(class_name, variable_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Method '{variable_name}' already exists in class '{class_name}'")

        # Second pass: transform the code
        wrapper = cst.MetadataWrapper(module)
        transformer = ReplaceTempWithQueryTransformer(
            class_name, method_name, variable_name, collector.variable_expression
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class TempVariableCollector(cst.CSTVisitor):
    """Collector to capture the temp variable expression."""

    def __init__(self, class_name: str, method_name: str, variable_name: str) -> None:
        """Initialize the collector.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method containing the variable
            variable_name: Name of the temp variable to replace
        """
        self.class_name = class_name
        self.method_name = method_name
        self.variable_name = variable_name
        self.variable_expression: cst.BaseExpression | None = None
        self.in_target_class = False
        self.in_target_method = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Leave class definition."""
        if node.name.value == self.class_name:
            self.in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to track if we're in the target method."""
        if self.in_target_class and node.name.value == self.method_name:
            self.in_target_method = True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Leave function definition."""
        if self.in_target_class and node.name.value == self.method_name:
            self.in_target_method = False

    def visit_Assign(self, node: cst.Assign) -> None:  # noqa: N802
        """Visit assignment to capture the temp variable expression."""
        if not self.in_target_method:
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


class ReplaceTempWithQueryTransformer(cst.CSTTransformer):
    """Transforms a class by replacing a temp variable with a query method."""

    METADATA_DEPENDENCIES = (metadata.ParentNodeProvider,)

    def __init__(
        self,
        class_name: str,
        method_name: str,
        variable_name: str,
        variable_expression: cst.BaseExpression,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method containing the variable
            variable_name: Name of the temp variable to replace
            variable_expression: The variable's expression to extract
        """
        self.class_name = class_name
        self.method_name = method_name
        self.variable_name = variable_name
        self.variable_expression = variable_expression
        self.in_target_class = False
        self.in_target_method = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and add the new query method."""
        if original_node.name.value == self.class_name:
            self.in_target_class = False

            # Create the new query method
            new_method = self._create_query_method()

            # Add the method to the class body
            new_body = list(updated_node.body.body)
            new_body.append(new_method)

            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=tuple(new_body))
            )
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to track if we're in the target method."""
        if self.in_target_class and node.name.value == self.method_name:
            self.in_target_method = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and remove the temp variable assignment."""
        if self.in_target_class and original_node.name.value == self.method_name:
            self.in_target_method = False

            # Remove the temp variable assignment
            statements_without_temp = [
                stmt
                for stmt in updated_node.body.body
                if isinstance(stmt, cst.BaseStatement) and not self._is_temp_assignment(stmt)
            ]

            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=tuple(statements_without_temp))
            )
        return updated_node

    def leave_Name(  # noqa: N802
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        """Leave name node and replace temp variable uses with method calls."""
        if (
            self.in_target_method
            and updated_node.value == self.variable_name
            and not self._is_in_assignment_target(original_node)
        ):
            # Replace with self.variable_name()
            return cst.Call(
                func=cst.Attribute(
                    value=cst.Name("self"),
                    attr=cst.Name(self.variable_name),
                ),
            )
        return updated_node

    def _create_query_method(self) -> cst.FunctionDef:
        """Create the new query method.

        Returns:
            A FunctionDef node for the new query method
        """
        return cst.FunctionDef(
            name=cst.Name(self.variable_name),
            params=cst.Parameters(
                params=[
                    cst.Param(
                        name=cst.Name("self"),
                    )
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=self.variable_expression,
                            )
                        ]
                    )
                ]
            ),
        )

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
            parent = self.get_metadata(metadata.ParentNodeProvider, node)
            while parent:
                if isinstance(parent, cst.AssignTarget):
                    return True
                if isinstance(parent, cst.FunctionDef):
                    # Stop at function boundary
                    break
                parent = self.get_metadata(metadata.ParentNodeProvider, parent)
        except KeyError:
            # Metadata not available, fall back to simple check
            pass
        return False
