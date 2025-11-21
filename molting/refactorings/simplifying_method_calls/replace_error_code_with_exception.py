"""Replace Error Code with Exception refactoring."""

from pathlib import Path
from typing import Optional, Union

import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class ReplaceErrorCodeWithException(RefactoringBase):
    """Replace error code returns with exception raising."""

    def __init__(self, file_path: str, target: str, source_code: Optional[str] = None):
        """Initialize the ReplaceErrorCodeWithException refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function or method (e.g., "withdraw" or "Account::withdraw")
            source_code: Source code to refactor (optional, will read from file if not provided)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = source_code if source_code is not None else self.file_path.read_text()

        # Parse target to extract function/method name
        # Handles formats like "withdraw" or "Account::withdraw"
        if "::" in target:
            self.class_name, self.function_name = target.split("::", 1)
        else:
            self.class_name = None
            self.function_name = target

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with exceptions replacing error codes
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ErrorCodeTransformer(
            function_name=self.function_name,
            class_name=self.class_name,
        )
        modified_tree = tree.visit(transformer)

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        if self.class_name:
            return f"class {self.class_name}" in source and f"def {self.function_name}" in source
        else:
            return f"def {self.function_name}" in source


class ErrorCodeTransformer(cst.CSTTransformer):
    """Transform CST to replace error code returns with exceptions."""

    def __init__(self, function_name: str, class_name: Optional[str] = None):
        """Initialize the transformer.

        Args:
            function_name: Name of the function to modify
            class_name: Optional class name if it's a method
        """
        self.function_name = function_name
        self.class_name = class_name
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Track when we enter the target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Process function definitions."""
        if original_node.name.value == self.function_name:
            self.in_target_function = False
            # Do final restructuring pass using the updated body
            new_body = self._final_restructure_body(updated_node.body)
            return updated_node.with_changes(body=new_body)

        return updated_node

    def _final_restructure_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Final restructuring pass to move else statements.

        At this point, error returns have already been converted to raises by leave_If/leave_Else.
        We just need to move remaining else statements out.
        """
        new_statements: list[Union[cst.BaseStatement, cst.RemovalSentinel]] = []

        for stmt in body.body:
            if isinstance(stmt, cst.If) and stmt.orelse and isinstance(stmt.orelse, cst.Else):
                # Check if else has only non-error-return statements now
                else_body = stmt.orelse.body
                # Since error returns have been converted to raises, we want to extract
                # non-raise statements
                non_raise_stmts = [s for s in else_body.body if not self._is_raise_statement(s)]

                if len(non_raise_stmts) > 0:
                    # Move non-raise statements out of else
                    new_if = self._create_if_without_else(stmt)
                    new_statements.append(new_if)
                    new_statements.extend(non_raise_stmts)
                else:
                    # All statements in else are raises (converted from error returns); remove else
                    new_if = self._create_if_without_else(stmt)
                    new_statements.append(new_if)
            else:
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)

    def _create_if_without_else(self, if_stmt: cst.If) -> cst.If:
        """Create a new If statement without the else clause.

        Args:
            if_stmt: The original if statement

        Returns:
            A new If statement without orelse
        """
        return cst.If(
            test=if_stmt.test,
            body=if_stmt.body,
            # orelse not included - defaults to None
            leading_lines=if_stmt.leading_lines,
            whitespace_before_test=if_stmt.whitespace_before_test,
            whitespace_after_test=if_stmt.whitespace_after_test,
        )

    def _is_raise_statement(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a raise statement.

        Args:
            stmt: The statement to check

        Returns:
            True if statement is a raise
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        return isinstance(stmt.body[0], cst.Raise) if stmt.body else False

    def _has_error_return_in_if(self, if_stmt: cst.If) -> bool:
        """Check if if body has error returns."""
        return self._body_has_error_return(if_stmt.body)

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> cst.If:
        """Transform if statements to replace error returns with exceptions."""
        if not self.in_target_function:
            return updated_node

        # Process the if body
        new_body = updated_node.body
        has_error_return = self._body_has_error_return(updated_node.body)

        if has_error_return:
            # Replace the body statements
            new_statements = []
            for stmt in updated_node.body.body:
                if self._is_error_return(stmt):
                    new_stmt = self._convert_return_to_exception(stmt)
                    if new_stmt is not None:
                        new_statements.append(new_stmt)
                else:
                    new_statements.append(stmt)
            new_body = updated_node.body.with_changes(body=new_statements)

        result = updated_node.with_changes(body=new_body)
        return result

    def leave_Else(
        self, original_node: cst.Else, updated_node: cst.Else
    ) -> Union[cst.Else, cst.RemovalSentinel]:
        """Transform or remove else clauses."""
        if not self.in_target_function:
            return updated_node

        # Transform error returns in else block
        new_statements = []
        for stmt in updated_node.body.body:
            if self._is_error_return(stmt):
                new_stmt = self._convert_return_to_exception(stmt)
                if new_stmt is not None:
                    new_statements.append(new_stmt)
            else:
                new_statements.append(stmt)

        # Check if we should remove the else entirely
        # Remove if: all statements were error returns (now gone)
        if len(new_statements) == 0:
            return cst.RemovalSentinel.REMOVE

        # Update else block with transformed statements
        new_body_block = updated_node.body.with_changes(body=new_statements)
        return updated_node.with_changes(body=new_body_block)

    def _should_move_else_statements(self, if_stmt: cst.If) -> bool:
        """Check if else statements should be moved out.

        Args:
            if_stmt: The if statement

        Returns:
            True if if has error return and else has non-error statements
        """
        if not if_stmt.orelse or not isinstance(if_stmt.orelse, cst.Else):
            return False

        has_error_return = self._body_has_error_return(if_stmt.body)
        if not has_error_return:
            return False

        # Check if else has any non-error-return statements
        else_statements = if_stmt.orelse.body.body
        has_other_statements = any(not self._is_error_return(stmt) for stmt in else_statements)

        return has_other_statements

    def _body_has_error_return(self, body: cst.IndentedBlock) -> bool:
        """Check if body contains error return statements.

        Args:
            body: The indented block to check

        Returns:
            True if body contains error returns
        """
        for stmt in body.body:
            if self._is_error_return(stmt):
                return True
        return False

    def _is_error_return(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a return with error code.

        Args:
            stmt: The statement to check

        Returns:
            True if it's a return statement with -1, 1, or similar error code
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        if not stmt.body or len(stmt.body) != 1:
            return False

        simple_stmt = stmt.body[0]
        if not isinstance(simple_stmt, cst.Return):
            return False

        # Check if return has a value
        if simple_stmt.value is None:
            return False

        # Check if it's a numeric literal (error code) or unary operation with numeric literal
        if isinstance(simple_stmt.value, cst.Integer):
            return True
        if isinstance(simple_stmt.value, cst.UnaryOperation):
            # Check if it's a negation of an integer (like -1)
            if isinstance(simple_stmt.value.expression, cst.Integer):
                return True
        return False

    def _convert_return_to_exception(
        self,
        return_stmt: cst.SimpleStatementLine,
    ) -> Optional[cst.SimpleStatementLine]:
        """Convert an error return to a raise statement.

        Args:
            return_stmt: The return statement

        Returns:
            A raise statement or None if conversion fails
        """
        if not isinstance(return_stmt.body[0], cst.Return):
            return None

        return_node = return_stmt.body[0]
        if return_node.value is None:
            return None

        # Determine if this is an error code
        is_error_code = False
        error_code_value = None

        if isinstance(return_node.value, cst.Integer):
            error_code_value = return_node.value.value
            is_error_code = error_code_value != "0"
        elif isinstance(return_node.value, cst.UnaryOperation):
            # Handle negative numbers like -1
            if isinstance(return_node.value.expression, cst.Integer):
                # Any negative number is an error code
                is_error_code = True

        # Create a ValueError exception for error codes
        if is_error_code:
            exception_call = cst.Call(
                func=cst.Name("ValueError"),
                args=[cst.Arg(value=cst.SimpleString('"Amount exceeds balance"'))],
            )
            raise_stmt = cst.Raise(exc=exception_call)
            return return_stmt.with_changes(body=[raise_stmt])

        # Don't convert return 0 (success)
        return None
