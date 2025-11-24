"""Replace Exception with Test refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ReplaceExceptionWithTestCommand(BaseCommand):
    """Command to replace exception handling with precondition tests."""

    name = "replace-exception-with-test"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-exception-with-test refactoring using libCST.

        Raises:
            ValueError: If function not found
        """
        function_name = self.params["target"]

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ReplaceExceptionTransformer(function_name)
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ReplaceExceptionTransformer(cst.CSTTransformer):
    """Transforms a function by replacing exception handling with precondition tests."""

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

    def leave_Try(  # noqa: N802
        self, original_node: cst.Try, updated_node: cst.Try
    ) -> cst.BaseStatement | cst.RemovalSentinel | cst.FlattenSentinel[cst.BaseStatement]:
        """Transform Try statements in the target function."""
        if not self.in_target_function:
            return updated_node

        # Check if this is an IndexError handling pattern
        if self._is_index_error_pattern(updated_node):
            return self._transform_to_test(updated_node)

        return updated_node

    def _is_index_error_pattern(self, try_node: cst.Try) -> bool:
        """Check if a try statement is catching IndexError.

        Args:
            try_node: The try statement to check

        Returns:
            True if it catches IndexError, False otherwise
        """
        for handler in try_node.handlers:
            if handler.type and isinstance(handler.type, cst.Name):
                if handler.type.value == "IndexError":
                    return True
        return False

    def _transform_to_test(
        self, try_node: cst.Try
    ) -> cst.BaseStatement | cst.FlattenSentinel[cst.BaseStatement]:
        """Transform a try/except to use a precondition test.

        Args:
            try_node: The try statement to transform

        Returns:
            The transformed statement(s)
        """
        # Extract the try body
        try_body = self._get_block_body(try_node.body)

        # Find the return statement in try block
        index_access = self._find_subscript_return(try_body)
        if not index_access:
            return try_node

        # Get the except handler's return value
        except_return = None
        for handler in try_node.handlers:
            handler_body = self._get_block_body(handler.body)
            for stmt in handler_body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for substmt in stmt.body:
                        if isinstance(substmt, cst.Return):
                            except_return = substmt.value
                            break

        if except_return is None:
            return try_node

        # Build the condition: period_count >= len(values)
        # Extract the index and sequence from the subscript
        sequence = index_access.value
        index = (
            index_access.slice[0].slice.value
            if isinstance(index_access.slice[0].slice, cst.Index)
            else index_access.slice[0].slice
        )

        # Create the test condition
        condition = cst.Comparison(
            left=index,
            comparisons=[
                cst.ComparisonTarget(
                    operator=cst.GreaterThanEqual(),
                    comparator=cst.Call(func=cst.Name("len"), args=[cst.Arg(sequence)]),
                )
            ],
        )

        # Create the if statement
        if_stmt = cst.If(
            test=condition,
            body=cst.IndentedBlock(
                body=[cst.SimpleStatementLine(body=[cst.Return(value=except_return)])]
            ),
            orelse=None,
        )

        # Create the return statement for the normal case
        normal_return = cst.SimpleStatementLine(body=[cst.Return(value=index_access)])

        return cst.FlattenSentinel([if_stmt, normal_return])

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

    def _find_subscript_return(self, statements: list[cst.BaseStatement]) -> cst.Subscript | None:
        """Find a return statement that returns a subscript access.

        Args:
            statements: List of statements to search

        Returns:
            The subscript expression if found, None otherwise
        """
        for stmt in statements:
            if isinstance(stmt, cst.SimpleStatementLine):
                for substmt in stmt.body:
                    if isinstance(substmt, cst.Return) and substmt.value:
                        if isinstance(substmt.value, cst.Subscript):
                            return substmt.value
        return None


# Register the command
register_command(ReplaceExceptionWithTestCommand)
