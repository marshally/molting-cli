"""Remove Control Flag refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class RemoveControlFlagCommand(BaseCommand):
    """Replace control flag variables with break, continue, or return statements.

    The Remove Control Flag refactoring eliminates explicit boolean or sentinel
    variables that are used to control the flow of a function. These flags often
    obscure the actual flow of control and make code harder to understand. By
    replacing flag assignments with direct flow control statements (break, continue,
    or return), the code's intent becomes clearer and more direct.

    Based on Martin Fowler's "Refactoring: Improve the Design of Existing Code",
    this refactoring simplifies conditional logic and makes the control flow
    immediately apparent to readers.

    **When to use:**
    - When you have boolean variables used solely to exit early from loops
    - When control flags make the actual control flow less obvious
    - When a simple break or return would be more direct than setting a flag
    - When you want to improve code readability and simplify logic

    **Example:**
    Before:
        def find_person(people):
            found = False
            for person in people:
                if person.name == "John":
                    found = True
                    if person.age > 30:
                        found = False
            return found

    After:
        def find_person(people):
            for person in people:
                if person.name == "John":
                    if person.age > 30:
                        continue
                    return True
            return False
    """

    name = "remove-control-flag"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-control-flag refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target as function_name::flag_variable
        if "::" not in target:
            raise ValueError(
                f"Invalid target format: {target}. Expected: function_name::flag_variable"
            )

        function_name, flag_variable = target.split("::", 1)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = RemoveControlFlagTransformer(function_name, flag_variable)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class RemoveControlFlagTransformer(cst.CSTTransformer):
    """Transforms a function by removing control flag and using return/break."""

    def __init__(self, function_name: str, flag_variable: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to transform
            flag_variable: Name of the control flag variable to remove
        """
        self.function_name = function_name
        self.flag_variable = flag_variable

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and remove control flag pattern."""
        if original_node.name.value != self.function_name:
            return updated_node

        body = cast(cst.IndentedBlock, updated_node.body)
        new_body = self._transform_body(body)
        return updated_node.with_changes(body=new_body)

    def _transform_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Transform the function body to remove control flag.

        Args:
            body: The function body

        Returns:
            Transformed function body
        """
        new_statements: list[cst.BaseStatement] = []

        for stmt in body.body:
            if self._is_flag_initialization(stmt):
                continue

            if isinstance(stmt, cst.For):
                new_for = self._transform_for_loop(stmt)
                new_statements.append(new_for)
            else:
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)

    def _is_flag_initialization(self, stmt: cst.BaseStatement) -> bool:
        """Check if statement is the flag initialization.

        Args:
            stmt: Statement to check

        Returns:
            True if this is the flag initialization statement
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        for s in stmt.body:
            if isinstance(s, cst.Assign):
                if self._assigns_to_flag_variable(s):
                    return True
        return False

    def _assigns_to_flag_variable(self, assign: cst.Assign) -> bool:
        """Check if assignment assigns to the flag variable.

        Args:
            assign: Assignment node to check

        Returns:
            True if this assignment targets the flag variable
        """
        for target in assign.targets:
            if isinstance(target.target, cst.Name):
                if target.target.value == self.flag_variable:
                    return True
        return False

    def _transform_for_loop(self, for_loop: cst.For) -> cst.For:
        """Transform for loop to remove guard clause and replace flag assignments with return.

        Args:
            for_loop: The for loop to transform

        Returns:
            Transformed for loop
        """
        new_body_statements: list[cst.BaseStatement] = []
        loop_body = cast(cst.IndentedBlock, for_loop.body)

        for stmt in loop_body.body:
            if isinstance(stmt, cst.If):
                transformed = self._transform_if_statement(stmt)
                if isinstance(transformed, list):
                    new_body_statements.extend(transformed)
                elif transformed is not None:
                    new_body_statements.append(transformed)
            else:
                new_body_statements.append(stmt)

        return for_loop.with_changes(body=cst.IndentedBlock(body=new_body_statements))

    def _transform_if_statement(self, if_stmt: cst.If) -> cst.If | list[cst.BaseStatement] | None:
        """Transform if statement to remove guard clause and replace flag assignments.

        Args:
            if_stmt: The if statement to transform

        Returns:
            Transformed if statement, list of statements, or None if it should be removed
        """
        if self._is_guard_clause(if_stmt.test):
            guard_body = cast(cst.IndentedBlock, if_stmt.body)
            return self._transform_guard_body(guard_body)

        if_body = cast(cst.IndentedBlock, if_stmt.body)
        new_body = self._replace_flag_assignments_with_return(if_body)
        return if_stmt.with_changes(body=new_body)

    def _is_guard_clause(self, test: cst.BaseExpression) -> bool:
        """Check if test expression is the guard clause (e.g., not found).

        Args:
            test: The test expression

        Returns:
            True if this is the guard clause
        """
        if not isinstance(test, cst.UnaryOperation):
            return False
        if not isinstance(test.operator, cst.Not):
            return False
        if not isinstance(test.expression, cst.Name):
            return False
        return test.expression.value == self.flag_variable

    def _transform_guard_body(self, body: cst.IndentedBlock) -> list[cst.BaseStatement]:
        """Transform the body of the guard clause.

        Args:
            body: The body of the guard clause

        Returns:
            List of transformed statements from the guard body
        """
        transformed_statements: list[cst.BaseStatement] = []

        for stmt in body.body:
            if isinstance(stmt, cst.If):
                if_body = cast(cst.IndentedBlock, stmt.body)
                new_body = self._replace_flag_assignments_with_return(if_body)
                transformed_statements.append(stmt.with_changes(body=new_body))
            else:
                transformed_statements.append(stmt)

        return transformed_statements

    def _replace_flag_assignments_with_return(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Replace flag assignments with return statements.

        Args:
            body: The body to transform

        Returns:
            Transformed body
        """
        new_statements: list[cst.BaseStatement] = []

        for stmt in body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                replaced = False
                for s in stmt.body:
                    if isinstance(s, cst.Assign) and self._assigns_to_flag_variable(s):
                        new_statements.append(
                            cst.SimpleStatementLine(body=[cst.Return(value=None)])
                        )
                        replaced = True
                        break
                if not replaced:
                    new_statements.append(stmt)
            else:
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)


# Register the command
register_command(RemoveControlFlagCommand)
