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

    def _parse_target(self, target: str) -> tuple[str, str, int, int]:
        """Parse target specification into class name, function name, and line range.

        Args:
            target: Target string in format "function_name#L2-L7" or "ClassName::method#L2-L7"

        Returns:
            Tuple of (class_name, function_name, start_line, end_line)
            class_name will be empty string for module-level functions

        Raises:
            ValueError: If target format is invalid
        """
        # Parse target format: "function_name#L2-L7" or "ClassName::method#L2-L7"
        parts = target.split("#")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid target format '{target}'. "
                "Expected 'function_name#L2-L7' or 'ClassName::method#L2-L7'"
            )

        class_method = parts[0]
        line_range = parts[1]

        # Parse class_method to extract class and method names
        if "::" in class_method:
            class_parts = class_method.split("::")
            if len(class_parts) != 2:
                raise ValueError(f"Invalid class::method format in '{class_method}'")
            class_name, function_name = class_parts
        else:
            class_name = ""
            function_name = class_method

        # Use canonical line range parser
        start_line, end_line = parse_line_range(line_range)
        return class_name, function_name, start_line, end_line

    def execute(self) -> None:
        """Apply consolidate-duplicate-conditional-fragments refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]
        class_name, function_name, start_line, end_line = self._parse_target(target)

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ConsolidateDuplicateFragmentsTransformer(
            class_name, function_name, start_line, end_line
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ConsolidateDuplicateFragmentsTransformer(cst.CSTTransformer):
    """Transforms a function by consolidating duplicate conditional fragments."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_name: str, function_name: str, start_line: int, end_line: int) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class (empty string for module-level functions)
            function_name: Name of the function to transform
            start_line: Start line of the conditional (1-indexed)
            end_line: End line of the conditional (1-indexed)
        """
        self.class_name = class_name
        self.function_name = function_name
        self.start_line = start_line
        self.end_line = end_line
        self.in_target_function = False
        self.current_class: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track current class being visited."""
        if node.name.value == self.class_name:
            self.current_class = self.class_name
        return True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Track exit from class."""
        if original_node.name.value == self.class_name:
            self.current_class = None
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to track if we're in the target function."""
        # For class methods, also check we're in the right class
        if node.name.value == self.function_name:
            if self.class_name and self.current_class == self.class_name:
                self.in_target_function = True
            elif not self.class_name:
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

            # Check if statements can be consolidated
            if if_stmt_at_end.deep_equals(else_stmt_at_end):
                # Identical statements - check if they depend on branch-specific variables
                if self._depends_on_branch_variables(if_stmt_at_end, if_body[: len(if_body) - i]):
                    # Can't consolidate - statement depends on variables written in branch
                    break
                duplicates.insert(0, if_stmt_at_end)
                i += 1
            elif self._can_consolidate_with_ternary(if_stmt_at_end, else_stmt_at_end):
                # Similar statements - consolidate with ternary expression
                consolidated = self._create_consolidated_statement(
                    if_stmt_at_end, else_stmt_at_end, if_stmt.test
                )
                duplicates.insert(0, consolidated)
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

    def _depends_on_branch_variables(
        self, stmt: cst.BaseStatement, branch_stmts: list[cst.BaseStatement]
    ) -> bool:
        """Check if a statement depends on variables written earlier in the branch.

        Args:
            stmt: Statement to check
            branch_stmts: Statements that appear before this one in the branch

        Returns:
            True if stmt reads variables written in branch_stmts, False otherwise
        """
        # Collect variables written in the branch
        written_vars = set()
        for branch_stmt in branch_stmts:
            written_vars.update(self._get_written_variables(branch_stmt))

        # Collect variables read by this statement
        read_vars = self._get_read_variables(stmt)

        # Check if any read variables were written in the branch
        return bool(written_vars & read_vars)

    def _get_written_variables(self, stmt: cst.BaseStatement) -> set[str]:
        """Get variables written (assigned) by a statement.

        Args:
            stmt: Statement to analyze

        Returns:
            Set of variable names written by the statement
        """
        collector = _VariableWriteCollector()
        stmt.visit(collector)
        return collector.written_vars

    def _get_read_variables(self, stmt: cst.BaseStatement) -> set[str]:
        """Get variables read (used) by a statement.

        Args:
            stmt: Statement to analyze

        Returns:
            Set of variable names read by the statement
        """
        collector = _VariableReadCollector()
        stmt.visit(collector)
        return collector.read_vars

    def _can_consolidate_with_ternary(
        self, stmt1: cst.BaseStatement, stmt2: cst.BaseStatement
    ) -> bool:
        """Check if two statements can be consolidated using a ternary expression.

        Args:
            stmt1: First statement
            stmt2: Second statement

        Returns:
            True if statements can be consolidated with ternary, False otherwise
        """
        # Both must be simple statement lines
        if not isinstance(stmt1, cst.SimpleStatementLine) or not isinstance(
            stmt2, cst.SimpleStatementLine
        ):
            return False

        # Each should have exactly one body element
        if len(stmt1.body) != 1 or len(stmt2.body) != 1:
            return False

        body1 = stmt1.body[0]
        body2 = stmt2.body[0]

        # Both should be Expr nodes
        if not isinstance(body1, cst.Expr) or not isinstance(body2, cst.Expr):
            return False

        # Both should be Call nodes
        if not isinstance(body1.value, cst.Call) or not isinstance(body2.value, cst.Call):
            return False

        call1 = body1.value
        call2 = body2.value

        # Function being called should be the same
        if not call1.func.deep_equals(call2.func):
            return False

        # Should have the same number of arguments
        if len(call1.args) != len(call2.args):
            return False

        # Count how many arguments differ
        diff_count = 0
        for arg1, arg2 in zip(call1.args, call2.args):
            if not arg1.value.deep_equals(arg2.value):
                diff_count += 1

        # Only consolidate if exactly one argument differs
        return diff_count == 1

    def _create_consolidated_statement(
        self,
        if_stmt: cst.BaseStatement,
        else_stmt: cst.BaseStatement,
        condition: cst.BaseExpression,
    ) -> cst.BaseStatement:
        """Create a consolidated statement with ternary expression for differing arguments.

        Args:
            if_stmt: Statement from the if branch
            else_stmt: Statement from the else branch
            condition: The if condition expression

        Returns:
            Consolidated statement with ternary expression
        """
        # Extract the calls (we know they're calls from _can_consolidate_with_ternary)
        if_simple = if_stmt  # type: ignore
        else_simple = else_stmt  # type: ignore

        if_call = if_simple.body[0].value  # type: ignore
        else_call = else_simple.body[0].value  # type: ignore

        # Find which argument differs and create new args with ternary
        new_args = []
        for if_arg, else_arg in zip(if_call.args, else_call.args):
            if if_arg.value.deep_equals(else_arg.value):
                # Same argument - keep as is
                new_args.append(if_arg)
            else:
                # Different argument - create ternary
                ternary = cst.IfExp(
                    body=if_arg.value,
                    test=condition,
                    orelse=else_arg.value,
                )
                new_args.append(if_arg.with_changes(value=ternary))

        # Create the new call with ternary arguments
        new_call = if_call.with_changes(args=new_args)

        # Wrap in expression statement
        new_expr = cst.Expr(value=new_call)
        new_stmt = cst.SimpleStatementLine(body=[new_expr])

        return new_stmt


class _VariableWriteCollector(cst.CSTVisitor):
    """Collects variables written (assigned) in a statement."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.written_vars: set[str] = set()

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Collect variables from assignment targets."""
        for target in node.targets:
            if isinstance(target.target, cst.Name):
                self.written_vars.add(target.target.value)
        return True

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:  # noqa: N802
        """Collect variables from annotated assignments."""
        if isinstance(node.target, cst.Name):
            self.written_vars.add(node.target.value)
        return True


class _VariableReadCollector(cst.CSTVisitor):
    """Collects variables read (used) in a statement."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.read_vars: set[str] = set()
        self._in_assignment_target = False

    def visit_AssignTarget(self, node: cst.AssignTarget) -> bool:  # noqa: N802
        """Track when we're in an assignment target."""
        self._in_assignment_target = True
        return True

    def leave_AssignTarget(self, node: cst.AssignTarget) -> None:  # noqa: N802
        """Track when we leave an assignment target."""
        self._in_assignment_target = False

    def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802
        """Collect variable names that are read."""
        # Only collect names that aren't being assigned to
        if not self._in_assignment_target:
            self.read_vars.add(node.value)
        return True


# Register the command
register_command(ConsolidateDuplicateConditionalFragmentsCommand)
