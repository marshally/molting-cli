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
        exception_message = self.params.get("message", "Amount exceeds balance")

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ReplaceErrorCodeTransformer(function_name, exception_message)
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ReplaceErrorCodeTransformer(cst.CSTTransformer):
    """Transforms a function by replacing error code returns with exceptions."""

    def __init__(self, function_name: str, exception_message: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to transform
            exception_message: Message to use in the exception
        """
        self.function_name = function_name
        self.exception_message = exception_message
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

        if self._is_error_code_pattern(updated_node):
            return self._transform_error_code_to_exception(updated_node)

        return updated_node

    def _is_error_code_pattern(self, if_node: cst.If) -> bool:
        """Check if an if statement matches the error code pattern.

        Args:
            if_node: The if statement to check

        Returns:
            True if it matches the error code pattern, False otherwise
        """
        if_body = self._get_block_body(if_node.body)

        if len(if_body) == 1 and isinstance(if_body[0], cst.SimpleStatementLine):
            stmt = if_body[0].body[0]
            return isinstance(stmt, cst.Return) and self._is_error_code(stmt.value)

        return False

    def _transform_error_code_to_exception(
        self, if_node: cst.If
    ) -> cst.BaseStatement | cst.FlattenSentinel[cst.BaseStatement]:
        """Transform an error code pattern to use exceptions.

        Args:
            if_node: The if statement to transform

        Returns:
            The transformed statement(s)
        """
        raise_stmt = self._create_raise_statement()

        if if_node.orelse and isinstance(if_node.orelse, cst.Else):
            else_body = self._get_block_body(if_node.orelse.body)
            success_body = self._filter_success_returns(else_body)

            new_if = if_node.with_changes(body=cst.IndentedBlock(body=[raise_stmt]), orelse=None)

            return cst.FlattenSentinel([new_if] + success_body)

        return if_node

    def _create_raise_statement(self) -> cst.SimpleStatementLine:
        """Create a raise statement with the configured exception message.

        Returns:
            A SimpleStatementLine containing the raise statement
        """
        return cst.SimpleStatementLine(
            body=[
                cst.Raise(
                    exc=cst.Call(
                        func=cst.Name("ValueError"),
                        args=[cst.Arg(cst.SimpleString(f'"{self.exception_message}"'))],
                    )
                )
            ]
        )

    def _filter_success_returns(
        self, statements: list[cst.BaseStatement]
    ) -> list[cst.BaseStatement]:
        """Filter out success return statements from a list of statements.

        Args:
            statements: List of statements to filter

        Returns:
            List of statements with success returns removed
        """
        filtered_statements = []
        for statement in statements:
            if self._is_success_return(statement):
                continue
            filtered_statements.append(statement)
        return filtered_statements

    def _is_success_return(self, statement: cst.BaseStatement) -> bool:
        """Check if a statement is a success return (return 0).

        Args:
            statement: The statement to check

        Returns:
            True if it's a success return, False otherwise
        """
        if isinstance(statement, cst.SimpleStatementLine) and len(statement.body) > 0:
            if isinstance(statement.body[0], cst.Return):
                return self._is_success_code(statement.body[0].value)
        return False

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
