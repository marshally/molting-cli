"""Introduce Explaining Variable refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceExplainingVariableCommand(BaseCommand):
    """Command to introduce an explaining variable for a complex expression."""

    name = "introduce-explaining-variable"

    def validate(self) -> None:
        """Validate that required parameters are present."""
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply introduce-explaining-variable refactoring using libCST."""
        target = self.params["target"]
        variable_name = self.params["name"]

        # Parse target: "function_name#L2"
        if "#L" not in target:
            raise ValueError(f"Invalid target format '{target}'. Expected 'function_name#L2'")

        function_name, line_part = target.split("#L")
        line_number = int(line_part)

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = IntroduceVariableTransformer(function_name, variable_name, line_number)
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class IntroduceVariableTransformer(cst.CSTTransformer):
    """Transforms a function by introducing an explaining variable."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, function_name: str, variable_name: str, line_number: int) -> None:
        """Initialize the transformer."""
        self.function_name = function_name
        self.variable_name = variable_name
        self.line_number = line_number
        self.in_target_function = False
        self.target_expression: cst.BaseExpression | None = None
        self.found_return_with_expression = False
        self.candidates: list[cst.BaseExpression] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to find target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform the function to include the new variable."""
        if original_node.name.value != self.function_name:
            return updated_node

        self.in_target_function = False

        # If we found an expression and transformed the return, add variable assignment
        if self.target_expression and self.found_return_with_expression:
            if isinstance(updated_node.body, cst.IndentedBlock):
                new_statements = []

                # Add variable assignment before the return
                for stmt in updated_node.body.body:
                    if isinstance(stmt, cst.SimpleStatementLine):
                        has_return = any(isinstance(s, cst.Return) for s in stmt.body)
                        if has_return:
                            # Insert variable assignment before return
                            assignment = cst.SimpleStatementLine(
                                body=[
                                    cst.Assign(
                                        targets=[
                                            cst.AssignTarget(target=cst.Name(self.variable_name))
                                        ],
                                        value=self.target_expression,
                                    )
                                ]
                            )
                            new_statements.append(assignment)
                    new_statements.append(stmt)

                return updated_node.with_changes(body=cst.IndentedBlock(body=new_statements))

        return updated_node

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> None:  # noqa: N802
        """Visit binary operations to find target expression."""
        if not self.in_target_function:
            return

        try:
            position = self.get_metadata(metadata.PositionProvider, node)
            if position.start.line == self.line_number + 1:
                self.candidates.append(node)
        except KeyError:
            pass

    def visit_Call(self, node: cst.Call) -> None:  # noqa: N802
        """Visit function calls to find target expression."""
        if not self.in_target_function:
            return

        try:
            position = self.get_metadata(metadata.PositionProvider, node)
            if position.start.line == self.line_number + 1:
                self.candidates.append(node)
        except KeyError:
            pass

    def leave_Return(  # noqa: N802
        self, original_node: cst.Return, updated_node: cst.Return
    ) -> cst.Return:
        """Replace the target expression with the variable name in return statement."""
        if not self.in_target_function or not updated_node.value:
            return updated_node

        # Select the smallest expression from candidates if not yet selected
        if not self.target_expression and self.candidates:
            self.target_expression = min(
                self.candidates, key=lambda e: len(cst.Module([]).code_for_node(e))
            )

        if not self.target_expression:
            return updated_node

        self.found_return_with_expression = True
        new_value = self._replace_expression(updated_node.value)
        return updated_node.with_changes(value=new_value)

    def _replace_expression(self, node: cst.BaseExpression) -> cst.BaseExpression:
        """Recursively replace the target expression with the variable name."""
        if node.deep_equals(self.target_expression):
            return cst.Name(self.variable_name)

        # Recursively handle binary operations
        if isinstance(node, cst.BinaryOperation):
            new_left = self._replace_expression(node.left)
            new_right = self._replace_expression(node.right)
            if new_left is not node.left or new_right is not node.right:
                return node.with_changes(left=new_left, right=new_right)

        # Recursively handle function calls
        if isinstance(node, cst.Call):
            new_args = []
            changed = False
            for arg in node.args:
                new_value = self._replace_expression(arg.value)
                if new_value is not arg.value:
                    new_args.append(arg.with_changes(value=new_value))
                    changed = True
                else:
                    new_args.append(arg)
            if changed:
                return node.with_changes(args=new_args)

        return node


# Register the command
register_command(IntroduceExplainingVariableCommand)
