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

        # First pass: Transform the function itself
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ReplaceErrorCodeTransformer(function_name, exception_message)
        modified_tree = wrapper.visit(transformer)

        # Second pass: Transform call sites
        call_site_transformer = CallSiteTransformer(function_name)
        modified_tree = modified_tree.visit(call_site_transformer)

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
        """Leave function definition and remove success return statements."""
        if original_node.name.value == self.function_name:
            self.in_target_function = False
            # Remove return 0 statements from the function body
            if isinstance(updated_node.body, cst.IndentedBlock):
                new_body = [
                    stmt for stmt in updated_node.body.body if not self._is_success_return(stmt)
                ]
                return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))
        return updated_node

    def leave_If(  # noqa: N802
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.BaseStatement | cst.RemovalSentinel | cst.FlattenSentinel[cst.BaseStatement]:
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

        # No else clause - just replace the body with raise
        return if_node.with_changes(body=cst.IndentedBlock(body=[raise_stmt]))

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


class CallSiteTransformer(cst.CSTTransformer):
    """Transforms call sites to use try/except instead of error code checking."""

    def __init__(self, function_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function whose call sites to transform
        """
        self.function_name = function_name

    def leave_IndentedBlock(  # noqa: N802
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.IndentedBlock:
        """Transform call sites in an indented block."""
        new_body = self._transform_statement_list(list(updated_node.body))
        return updated_node.with_changes(body=new_body)

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Transform call sites at module level."""
        new_body = self._transform_statement_list(list(updated_node.body))
        return updated_node.with_changes(body=new_body)

    def _transform_statement_list(
        self, statements: list[cst.BaseStatement]
    ) -> list[cst.BaseStatement]:
        """Transform a list of statements, combining assignment + if into try/except.

        Args:
            statements: List of statements to transform

        Returns:
            Transformed list of statements
        """
        new_statements: list[cst.BaseStatement] = []
        i = 0

        while i < len(statements):
            stmt = statements[i]

            # Check for pattern: assignment followed by if checking error code
            if i + 1 < len(statements):
                next_stmt = statements[i + 1]
                # Gather remaining statements after the if (for case with no else)
                remaining = statements[i + 2 :] if i + 2 < len(statements) else []
                result, consumed = self._try_transform_call_site(stmt, next_stmt, remaining)
                if result is not None:
                    new_statements.append(result)
                    i += 2 + consumed  # Skip assignment, if, and consumed success stmts
                    continue

            new_statements.append(stmt)
            i += 1

        return new_statements

    def _try_transform_call_site(
        self,
        assign_stmt: cst.BaseStatement,
        if_stmt: cst.BaseStatement,
        remaining: list[cst.BaseStatement],
    ) -> tuple[cst.Try | None, int]:
        """Try to transform an assignment + if pair into a try/except.

        Args:
            assign_stmt: The assignment statement
            if_stmt: The if statement
            remaining: Statements after the if (for cases with no else)

        Returns:
            Tuple of (Try statement or None, number of remaining statements consumed)
        """
        # Check if first statement is an assignment calling our function
        if not isinstance(assign_stmt, cst.SimpleStatementLine):
            return None, 0

        if len(assign_stmt.body) != 1:
            return None, 0

        assign = assign_stmt.body[0]
        if not isinstance(assign, cst.Assign):
            return None, 0

        if len(assign.targets) != 1:
            return None, 0

        target = assign.targets[0].target
        if not isinstance(target, cst.Name):
            return None, 0

        var_name = target.value

        # Check if RHS is a call to our function
        if not isinstance(assign.value, cst.Call):
            return None, 0

        call = assign.value
        if not isinstance(call.func, cst.Name):
            return None, 0

        if call.func.value != self.function_name:
            return None, 0

        # Now check if the if statement checks var_name == -1
        if not isinstance(if_stmt, cst.If):
            return None, 0

        if not self._is_error_check(if_stmt.test, var_name):
            return None, 0

        # Transform to try/except
        return self._create_try_except(call, if_stmt, remaining)

    def _is_error_check(self, test: cst.BaseExpression, var_name: str) -> bool:
        """Check if a test expression is checking for error code.

        Args:
            test: The test expression
            var_name: The variable name to check

        Returns:
            True if it's checking var_name == -1
        """
        if not isinstance(test, cst.Comparison):
            return False

        if not isinstance(test.left, cst.Name):
            return False

        if test.left.value != var_name:
            return False

        if len(test.comparisons) != 1:
            return False

        cmp = test.comparisons[0]
        if not isinstance(cmp.operator, cst.Equal):
            return False

        # Check for -1
        if isinstance(cmp.comparator, cst.UnaryOperation):
            if isinstance(cmp.comparator.operator, cst.Minus):
                if isinstance(cmp.comparator.expression, cst.Integer):
                    return cmp.comparator.expression.value == "1"

        return False

    def _create_try_except(
        self, call: cst.Call, if_stmt: cst.If, remaining: list[cst.BaseStatement]
    ) -> tuple[cst.Try, int]:
        """Create a try/except statement from a call and if statement.

        Args:
            call: The function call
            if_stmt: The if statement with error handling
            remaining: Statements after the if (consumed when no else)

        Returns:
            Tuple of (Try statement, number of remaining statements consumed)
        """
        # The error handling is in the if body
        error_body = self._get_block_body(if_stmt.body)

        # The success handling is in the else body, or statements after the if
        consumed = 0
        if if_stmt.orelse and isinstance(if_stmt.orelse, cst.Else):
            success_body = self._get_block_body(if_stmt.orelse.body)
        else:
            # No else - success statements come after the if
            # Consume all remaining statements in this block
            success_body = remaining
            consumed = len(remaining)

        # Create the try body: call the function, then success statements
        call_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=call)])
        try_body = [call_stmt] + success_body

        # Create except handler
        except_handler = cst.ExceptHandler(
            type=cst.Name("ValueError"),
            body=(
                cst.IndentedBlock(body=error_body)
                if error_body
                else cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
            ),
        )

        return (
            cst.Try(
                body=cst.IndentedBlock(body=try_body),
                handlers=[except_handler],
            ),
            consumed,
        )

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


# Register the command
register_command(ReplaceErrorCodeWithExceptionCommand)
