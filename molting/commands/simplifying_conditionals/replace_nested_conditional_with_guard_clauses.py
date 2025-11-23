"""Replace Nested Conditional with Guard Clauses refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ReplaceNestedConditionalWithGuardClausesCommand(BaseCommand):
    """Command to replace nested conditionals with guard clauses."""

    name = "replace-nested-conditional-with-guard-clauses"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-nested-conditional-with-guard-clauses refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target as function_name#L<start>-L<end>
        if "#" not in target:
            raise ValueError(
                f"Invalid target format: {target}. Expected: function_name#L<start>-L<end>"
            )

        function_name, _ = target.split("#", 1)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = ReplaceNestedConditionalWithGuardClausesTransformer(function_name)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class ReplaceNestedConditionalWithGuardClausesTransformer(cst.CSTTransformer):
    """Transforms nested conditionals into guard clauses."""

    RESULT_VARIABLE_NAME = "result"

    def __init__(self, function_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to transform
        """
        self.function_name = function_name

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and replace nested conditionals with guard clauses."""
        if original_node.name.value != self.function_name:
            return updated_node

        body = cast(cst.IndentedBlock, updated_node.body)
        new_body = self._transform_body(body)
        return updated_node.with_changes(body=new_body)

    def _transform_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Transform the function body to use guard clauses.

        Args:
            body: The function body

        Returns:
            Transformed function body
        """
        new_statements: list[cst.BaseStatement] = []

        for stmt in body.body:
            if isinstance(stmt, cst.If):
                guard_clauses = self._extract_guard_clauses(stmt)
                new_statements.extend(guard_clauses)
            elif not self._is_result_return(stmt):
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)

    def _is_result_return(self, stmt: cst.BaseStatement) -> bool:
        """Check if statement is a return of the result variable.

        Args:
            stmt: Statement to check

        Returns:
            True if this is a return result statement
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        for s in stmt.body:
            if not isinstance(s, cst.Return):
                continue
            if isinstance(s.value, cst.Name) and s.value.value == self.RESULT_VARIABLE_NAME:
                return True
        return False

    def _extract_guard_clauses(self, if_stmt: cst.If) -> list[cst.BaseStatement]:
        """Extract guard clauses from nested if-else structure.

        Args:
            if_stmt: The if statement to transform

        Returns:
            List of guard clauses and final return statement
        """
        result: list[cst.BaseStatement] = []

        # Process the first condition
        if_body = cast(cst.IndentedBlock, if_stmt.body)
        return_value = self._get_return_value_from_assignment(if_body)

        if return_value is not None:
            # Create guard clause: if condition: return value
            result.append(
                if_stmt.with_changes(
                    body=cst.IndentedBlock(
                        body=[cst.SimpleStatementLine(body=[cst.Return(value=return_value)])]
                    ),
                    orelse=None,
                )
            )

        # Process else branch
        if if_stmt.orelse:
            else_clause = if_stmt.orelse
            if isinstance(else_clause, cst.Else):
                else_body = cast(cst.IndentedBlock, else_clause.body)
                # Check if else body contains another if statement
                if len(else_body.body) == 1 and isinstance(else_body.body[0], cst.If):
                    nested_if = else_body.body[0]
                    result.extend(self._extract_guard_clauses(nested_if))
                else:
                    # Else body is the final return
                    final_return = self._get_return_value_from_assignment(else_body)
                    if final_return is not None:
                        result.append(
                            cst.SimpleStatementLine(body=[cst.Return(value=final_return)])
                        )

        return result

    def _get_return_value_from_assignment(
        self, body: cst.IndentedBlock
    ) -> cst.BaseExpression | None:
        """Get the return value from a result assignment in the body.

        Args:
            body: The body containing the assignment

        Returns:
            The value being assigned to result, or None if not found
        """
        for stmt in body.body:
            if not isinstance(stmt, cst.SimpleStatementLine):
                continue

            for s in stmt.body:
                if not isinstance(s, cst.Assign):
                    continue

                for target in s.targets:
                    if not isinstance(target.target, cst.Name):
                        continue
                    if target.target.value == self.RESULT_VARIABLE_NAME:
                        return s.value
        return None


# Register the command
register_command(ReplaceNestedConditionalWithGuardClausesCommand)
