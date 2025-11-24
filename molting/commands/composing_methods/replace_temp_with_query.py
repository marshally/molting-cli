"""Replace Temp with Query refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter


@register_command
class ReplaceTempWithQueryCommand(BaseCommand):
    """Command to replace a temp variable with a query method."""

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
            ValueError: If target format is invalid or variable not found
        """
        target = self.params["target"]

        # Parse target: "ClassName::method_name::variable_name"
        parts = parse_target(target, expected_parts=3)
        class_name, method_name, variable_name = parts

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = ReplaceTempWithQueryTransformer(class_name, method_name, variable_name)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class ReplaceTempWithQueryTransformer(cst.CSTTransformer):
    """Transforms a class by replacing a temp variable with a query method."""

    def __init__(self, class_name: str, method_name: str, variable_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method containing the temp variable
            variable_name: Name of the temp variable to replace
        """
        self.class_name = class_name
        self.method_name = method_name
        self.variable_name = variable_name
        self.temp_expression: cst.BaseExpression | None = None
        self.new_method: cst.FunctionDef | None = None

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and replace temp variable usage."""
        if original_node.name.value != self.method_name:
            return updated_node

        # First pass: find the temp variable assignment and extract its expression
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for inner_stmt in stmt.body:
                    if isinstance(inner_stmt, cst.Assign):
                        for target in inner_stmt.targets:
                            if (
                                isinstance(target.target, cst.Name)
                                and target.target.value == self.variable_name
                            ):
                                self.temp_expression = inner_stmt.value
                                break

        if self.temp_expression is None:
            return updated_node

        # Second pass: remove the assignment and replace variable usage
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body.body:
            # Check if this statement is the temp variable assignment
            is_assignment = False
            if isinstance(stmt, cst.SimpleStatementLine):
                for inner_stmt in stmt.body:
                    if isinstance(inner_stmt, cst.Assign):
                        for target in inner_stmt.targets:
                            if (
                                isinstance(target.target, cst.Name)
                                and target.target.value == self.variable_name
                            ):
                                is_assignment = True
                                break

            # Skip the assignment statement
            if is_assignment:
                continue

            # Replace variable references with method calls
            replacer = VariableReplacer(self.variable_name)
            new_stmt = stmt.visit(replacer)
            new_body.append(new_stmt)

        return updated_node.with_changes(body=updated_node.body.with_changes(body=tuple(new_body)))

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and add new query method if needed."""
        if original_node.name.value != self.class_name:
            return updated_node

        if self.temp_expression is None:
            return updated_node

        # Create the new query method
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=self.temp_expression)])
        method_body = cst.IndentedBlock(body=[return_stmt])
        self.new_method = cst.FunctionDef(
            name=cst.Name(self.variable_name),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=method_body,
        )

        # Add leading blank line before the new method
        new_method_with_spacing = self.new_method.with_changes(
            leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
        )

        # Add the new method to the class
        new_body = tuple(list(updated_node.body.body) + [new_method_with_spacing])
        return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))


class VariableReplacer(cst.CSTTransformer):
    """Replaces variable references with method calls."""

    def __init__(self, variable_name: str) -> None:
        """Initialize the replacer.

        Args:
            variable_name: Name of the variable to replace
        """
        self.variable_name = variable_name

    def leave_Name(  # noqa: N802
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        """Replace variable references with method calls."""
        if updated_node.value == self.variable_name:
            return cst.Call(
                func=cst.Attribute(
                    value=cst.Name("self"),
                    attr=cst.Name(self.variable_name),
                )
            )
        return updated_node
