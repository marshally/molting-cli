"""Replace Nested Conditional with Guard Clauses refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ReplaceNestedConditionalWithGuardClausesCommand(BaseCommand):
    """Replace nested conditionals with guard clauses to improve code readability.

    This refactoring transforms deeply nested conditional logic into a series of guard
    clauses (early returns), making the code's intent clearer by handling exceptional
    cases first and leaving the main logic path at the top level of the function.

    **What it does:**
    Converts multiple levels of nested if-else statements into flat guard clauses where
    each condition has an early return, followed by the normal processing logic.

    **When to use:**
    - When a function has multiple levels of nested if-else statements
    - When the nested structure obscures the main business logic
    - When exceptional cases should be handled before the normal path
    - When you want to reduce cognitive load by reducing indentation depth
    - When the function's primary purpose is buried in nested blocks

    **Why it helps:**
    Guard clauses make the code more scannable and reduce mental overhead. The main
    success path is immediately visible at the function's top level, while exceptional
    cases are handled upfront with early returns. This matches how developers naturally
    think about control flow.

    **Example:**
    Before:
        def calculate_salary(employee):
            salary = 0
            if employee.years_employed > 5:
                if employee.performance_rating > 3:
                    if employee.department == "Engineering":
                        salary = employee.base_salary * 1.5
                    else:
                        salary = employee.base_salary * 1.2
                else:
                    salary = employee.base_salary
            else:
                salary = employee.base_salary * 0.8
            return salary

    After:
        def calculate_salary(employee):
            if employee.years_employed <= 5:
                return employee.base_salary * 0.8
            if employee.performance_rating <= 3:
                return employee.base_salary
            if employee.department == "Engineering":
                return employee.base_salary * 1.5
            return employee.base_salary * 1.2
    """

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

        # Parse target as function_name#L<start>-L<end> or ClassName::method#L<start>-L<end>
        if "#" not in target:
            raise ValueError(
                f"Invalid target format: {target}. "
                "Expected: function_name#L<start>-L<end> or ClassName::method#L<start>-L<end>"
            )

        class_method, _ = target.split("#", 1)

        # Parse class_method to extract class and method names
        if "::" in class_method:
            class_parts = class_method.split("::")
            if len(class_parts) != 2:
                raise ValueError(f"Invalid class::method format in '{class_method}'")
            class_name, function_name = class_parts
        else:
            class_name = ""
            function_name = class_method

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = ReplaceNestedConditionalWithGuardClausesTransformer(class_name, function_name)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class ReplaceNestedConditionalWithGuardClausesTransformer(cst.CSTTransformer):
    """Transforms nested conditionals into guard clauses."""

    RESULT_VARIABLE_NAME = "result"

    def __init__(self, class_name: str, function_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class (empty string for module-level functions)
            function_name: Name of the function to transform
        """
        self.class_name = class_name
        self.function_name = function_name
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

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and replace nested conditionals with guard clauses."""
        # Check if this is the target function
        if original_node.name.value != self.function_name:
            return updated_node

        # For class methods, also check we're in the right class
        if self.class_name and self.current_class != self.class_name:
            return updated_node
        elif not self.class_name and self.current_class is not None:
            # We're in a class but shouldn't be
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
        guard_clauses: list[cst.BaseStatement] = []

        # Process the first condition
        if_body = cast(cst.IndentedBlock, if_stmt.body)
        return_value = self._get_return_value_from_assignment(if_body)

        if return_value is not None:
            # Create guard clause: if condition: return value
            guard_clauses.append(
                if_stmt.with_changes(
                    body=cst.IndentedBlock(
                        body=[cst.SimpleStatementLine(body=[cst.Return(value=return_value)])]
                    ),
                    orelse=None,
                )
            )

        # Process else branch
        if if_stmt.orelse and isinstance(if_stmt.orelse, cst.Else):
            else_body = cast(cst.IndentedBlock, if_stmt.orelse.body)
            # Check if else body contains another if statement
            if len(else_body.body) == 1 and isinstance(else_body.body[0], cst.If):
                nested_if = else_body.body[0]
                guard_clauses.extend(self._extract_guard_clauses(nested_if))
            else:
                # Else body is the final return
                final_return = self._get_return_value_from_assignment(else_body)
                if final_return is not None:
                    guard_clauses.append(
                        cst.SimpleStatementLine(body=[cst.Return(value=final_return)])
                    )

        return guard_clauses

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
