"""Consolidate Duplicate Conditional Fragments refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ConsolidateDuplicateConditionalFragmentsCommand(BaseCommand):
    """Command to move duplicate code from conditional branches to after the conditional."""

    name = "consolidate-duplicate-conditional-fragments"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply consolidate-duplicate-conditional-fragments refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target format: "function_name#L2-L7"
        parts = target.split("#")
        if len(parts) != 2:
            raise ValueError(f"Invalid target format '{target}'. Expected 'function_name#L2-L7'")

        function_name = parts[0]
        line_range = parts[1]

        # Parse line range
        if not line_range.startswith("L") or "-" not in line_range:
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L2-L7'")

        range_parts = line_range.split("-")
        if len(range_parts) != 2:
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L2-L7'")

        try:
            start_line = int(range_parts[0][1:])
            end_line = int(range_parts[1][1:])
        except ValueError as e:
            raise ValueError(f"Invalid line numbers in '{line_range}': {e}") from e

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ConsolidateDuplicateFragmentsTransformer(function_name, start_line, end_line)
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ConsolidateDuplicateFragmentsTransformer(cst.CSTTransformer):
    """Transforms a function by consolidating duplicate conditional fragments."""

    def __init__(self, function_name: str, start_line: int, end_line: int) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to transform
            start_line: Start line of the conditional (1-indexed)
            end_line: End line of the conditional (1-indexed)
        """
        self.function_name = function_name
        self.start_line = start_line
        self.end_line = end_line
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
    ) -> cst.BaseStatement | cst.RemovalSentinel | cst.FlattenSentinel[cst.BaseStatement]:
        """Transform If statements in the target function."""
        if not self.in_target_function:
            return updated_node

        # Consolidate duplicate fragments from this if statement
        transformed_stmt, duplicate_stmts = self._consolidate_if_statement(updated_node)

        # If there are duplicates, we need to return both the transformed if and the duplicates
        # Use FlattenSentinel to insert multiple statements
        if duplicate_stmts:
            return cst.FlattenSentinel([transformed_stmt] + duplicate_stmts)

        return transformed_stmt

    def _consolidate_if_statement(self, if_stmt: cst.If) -> tuple[cst.If, list[cst.BaseStatement]]:
        """Consolidate duplicate statements from if/else branches.

        Args:
            if_stmt: The if statement to consolidate

        Returns:
            Tuple of (transformed if statement, list of duplicate statements to add after)
        """
        # Get the if and else bodies
        if_body = if_stmt.body.body if isinstance(if_stmt.body, cst.IndentedBlock) else []
        else_body = []

        if if_stmt.orelse:
            if isinstance(if_stmt.orelse, cst.Else):
                else_body = (
                    if_stmt.orelse.body.body
                    if isinstance(if_stmt.orelse.body, cst.IndentedBlock)
                    else []
                )

        # Find duplicate statements at the end of both branches
        duplicates = []
        i = 1
        while i <= len(if_body) and i <= len(else_body):
            if_stmt_at_end = if_body[-i]
            else_stmt_at_end = else_body[-i]

            # Compare the statements (simple structural comparison)
            if self._statements_equal(if_stmt_at_end, else_stmt_at_end):
                duplicates.insert(0, if_stmt_at_end)
                i += 1
            else:
                break

        if not duplicates:
            return if_stmt, []

        # Remove duplicates from both branches
        num_duplicates = len(duplicates)
        new_if_body = if_body[:-num_duplicates]
        new_else_body = else_body[:-num_duplicates]

        # Build new if statement
        new_if = if_stmt.with_changes(
            body=cst.IndentedBlock(body=tuple(new_if_body)),
            orelse=(
                cst.Else(body=cst.IndentedBlock(body=tuple(new_else_body)))
                if if_stmt.orelse
                else None
            ),
        )

        return new_if, duplicates

    def _statements_equal(self, stmt1: cst.BaseStatement, stmt2: cst.BaseStatement) -> bool:
        """Check if two statements are structurally equal.

        Args:
            stmt1: First statement
            stmt2: Second statement

        Returns:
            True if statements are equal, False otherwise
        """
        # Simple comparison based on code representation
        return stmt1.deep_equals(stmt2)


# Register the command
register_command(ConsolidateDuplicateConditionalFragmentsCommand)
