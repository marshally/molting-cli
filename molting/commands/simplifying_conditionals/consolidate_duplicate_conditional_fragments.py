"""Consolidate Duplicate Conditional Fragments refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_range


class ConsolidateDuplicateConditionalFragmentsCommand(BaseCommand):
    """Move duplicate code from conditional branches outside the conditional.

    This refactoring consolidates identical code fragments that appear at the end of
    all branches of a conditional statement. When the same statements appear in both
    the if and else branches (or all branches of an if-else if chain), they are
    extracted and moved after the entire conditional, eliminating duplication while
    preserving the logic's original behavior.

    **When to use:**
    - You notice the same statements repeated at the end of each conditional branch
    - You want to reduce duplication and improve code maintainability
    - You're simplifying conditionals as part of larger refactoring efforts
    - The duplicated code is independent of the conditional decision

    **Example:**
    Before:
        if condition:
            result = process_a()
            log_result(result)
            return result
        else:
            result = process_b()
            log_result(result)
            return result

    After:
        if condition:
            result = process_a()
        else:
            result = process_b()
        log_result(result)
        return result
    """

    name = "consolidate-duplicate-conditional-fragments"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def _parse_target(self, target: str) -> tuple[str, int, int]:
        """Parse target specification into function name and line range.

        Args:
            target: Target string in format "function_name#L2-L7"

        Returns:
            Tuple of (function_name, start_line, end_line)

        Raises:
            ValueError: If target format is invalid
        """
        # Parse target format: "function_name#L2-L7"
        parts = target.split("#")
        if len(parts) != 2:
            raise ValueError(f"Invalid target format '{target}'. Expected 'function_name#L2-L7'")

        function_name = parts[0]
        line_range = parts[1]

        # Use canonical line range parser
        start_line, end_line = parse_line_range(line_range)
        return function_name, start_line, end_line

    def execute(self) -> None:
        """Apply consolidate-duplicate-conditional-fragments refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]
        function_name, start_line, end_line = self._parse_target(target)

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

    def _consolidate_if_statement(self, if_stmt: cst.If) -> tuple[cst.If, list[cst.BaseStatement]]:
        """Consolidate duplicate statements from if/else branches.

        Args:
            if_stmt: The if statement to consolidate

        Returns:
            Tuple of (transformed if statement, list of duplicate statements to add after)
        """
        # Get the if and else bodies
        if_body = self._get_block_body(if_stmt.body)
        else_body = []

        if if_stmt.orelse and isinstance(if_stmt.orelse, cst.Else):
            else_body = self._get_block_body(if_stmt.orelse.body)

        # Find duplicate statements at the end of both branches
        duplicates: list[cst.BaseStatement] = []
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
