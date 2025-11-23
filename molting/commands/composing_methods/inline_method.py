"""Inline Method refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class InlineMethodCommand(BaseCommand):
    """Command to inline a method by replacing calls with the method body."""

    name = "inline-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply inline-method refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target format: "ClassName::method_name"
        class_name, method_name = parse_target(target, expected_parts=2)

        # Read file
        source_code = self.file_path.read_text()

        # First pass: capture the method body
        module = cst.parse_module(source_code)
        collector = MethodBodyCollector(class_name, method_name)
        module.visit(collector)

        if collector.method_body is None:
            raise ValueError(
                f"Method '{method_name}' not found in class '{class_name}' "
                "or does not have a simple return statement"
            )

        # Second pass: inline the method
        transformer = InlineMethodTransformer(class_name, method_name, collector.method_body)
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class MethodBodyCollector(cst.CSTVisitor):
    """Collector to capture the method body."""

    def __init__(self, class_name: str, method_name: str) -> None:
        """Initialize the collector.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to inline
        """
        self.class_name = class_name
        self.method_name = method_name
        self.method_body: cst.BaseExpression | None = None
        self.in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Leave class definition."""
        if node.name.value == self.class_name:
            self.in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to capture the method body."""
        if self.in_target_class and node.name.value == self.method_name:
            # Extract the method body - should be a return statement
            if len(node.body.body) == 1:
                stmt = node.body.body[0]
                if isinstance(stmt, cst.SimpleStatementLine) and len(stmt.body) == 1:
                    if isinstance(stmt.body[0], cst.Return) and stmt.body[0].value:
                        self.method_body = stmt.body[0].value


class InlineMethodTransformer(cst.CSTTransformer):
    """Transforms a class by inlining a method."""

    def __init__(
        self, class_name: str, method_name: str, method_body: cst.BaseExpression | None
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to inline
            method_body: The method body expression to inline
        """
        self.class_name = class_name
        self.method_name = method_name
        self.method_body = method_body

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and remove the inlined method."""
        if original_node.name.value == self.class_name:
            # Remove the method from the class
            new_body = [
                stmt
                for stmt in updated_node.body.body
                if not (isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.method_name)
            ]
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=tuple(new_body))
            )
        return updated_node

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Leave call expression and replace method calls with the method body."""
        # Check if this is a call to self.method_name()
        if isinstance(updated_node.func, cst.Attribute):
            if (
                isinstance(updated_node.func.value, cst.Name)
                and updated_node.func.value.value == "self"
                and updated_node.func.attr.value == self.method_name
            ):
                # Replace the call with the method body
                if self.method_body:
                    return self.method_body
        return updated_node


# Register the command
register_command(InlineMethodCommand)
