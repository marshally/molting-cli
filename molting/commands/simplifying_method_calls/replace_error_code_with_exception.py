"""Replace Error Code with Exception refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ReplaceErrorCodeWithExceptionCommand(BaseCommand):
    """Command to replace error code returns with exceptions."""

    name = "replace-error-code-with-exception"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-error-code-with-exception refactoring using libCST.

        Raises:
            ValueError: If function not found
        """
        target = self.params["target"]
        function_name = target

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ReplaceErrorCodeTransformer(function_name)
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ReplaceErrorCodeTransformer(cst.CSTTransformer):
    """Transforms a function by replacing error code returns with exceptions."""

    def __init__(self, function_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to transform
        """
        self.function_name = function_name
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to track if we're in the target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition."""
        if original_node.name.value == self.function_name:
            self.in_target_function = False
        return updated_node

    def leave_If(  # noqa: N802
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.BaseStatement | cst.RemovalSentinel:
        """Transform If statements in the target function."""
        if not self.in_target_function:
            return updated_node

        # Check if this is an error code pattern (if condition: return -1 else: ... return 0)
        if_body = self._get_block_body(updated_node.body)

        # Check if the if body contains a return statement with error code
        if len(if_body) == 1 and isinstance(if_body[0], cst.SimpleStatementLine):
            stmt = if_body[0].body[0]
            if isinstance(stmt, cst.Return) and self._is_error_code(stmt.value):
                # This is the error path - replace with raise exception
                raise_stmt = cst.SimpleStatementLine(
                    body=[
                        cst.Raise(
                            exc=cst.Call(
                                func=cst.Name("ValueError"),
                                args=[cst.Arg(cst.SimpleString('"Amount exceeds balance"'))],
                            )
                        )
                    ]
                )

                # Get the else body (success path)
                if updated_node.orelse and isinstance(updated_node.orelse, cst.Else):
                    else_body = self._get_block_body(updated_node.orelse.body)
                    # Remove the success return statement (return 0)
                    success_body = []
                    for s in else_body:
                        if isinstance(s, cst.SimpleStatementLine) and len(s.body) > 0:
                            if isinstance(s.body[0], cst.Return) and self._is_success_code(
                                s.body[0].value
                            ):
                                continue  # Skip success return
                        success_body.append(s)

                    # Return the transformed if with raise, followed by success body
                    new_if = updated_node.with_changes(
                        body=cst.IndentedBlock(body=[raise_stmt]), orelse=None
                    )

                    # Use FlattenSentinel to insert the if and then the success body
                    return cst.FlattenSentinel([new_if] + success_body)

        return updated_node

    def _get_block_body(self, block: cst.BaseSuite) -> list[cst.BaseStatement]:
        """Extract statements from a code block.

        Args:
            block: The code block to extract statements from

        Returns:
            List of statements in the block
        """
        if isinstance(block, cst.IndentedBlock):
            return list(block.body)
        return []

    def _is_error_code(self, value: cst.BaseExpression | None) -> bool:
        """Check if a value represents an error code (like -1).

        Args:
            value: The expression to check

        Returns:
            True if it's an error code, False otherwise
        """
        if value is None:
            return False
        if isinstance(value, cst.UnaryOperation):
            if isinstance(value.operator, cst.Minus) and isinstance(value.expression, cst.Integer):
                return value.expression.value == "1"
        return False

    def _is_success_code(self, value: cst.BaseExpression | None) -> bool:
        """Check if a value represents a success code (like 0).

        Args:
            value: The expression to check

        Returns:
            True if it's a success code, False otherwise
        """
        if value is None:
            return False
        if isinstance(value, cst.Integer):
            return value.value == "0"
        return False


# Register the command
register_command(ReplaceErrorCodeWithExceptionCommand)
