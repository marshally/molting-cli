"""Remove Control Flag refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class RemoveControlFlagCommand(BaseCommand):
    """Command to replace control flag variables with break or return."""

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

        # Read file
        source_code = self.file_path.read_text()

        # Parse and transform
        module = cst.parse_module(source_code)
        transformer = RemoveControlFlagTransformer(function_name, flag_variable)
        modified_tree = module.visit(transformer)

        # Write back
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

        # Transform the function body to remove control flag
        new_body = self._transform_body(updated_node.body)
        return updated_node.with_changes(body=new_body)

    def _transform_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Transform the function body to remove control flag.

        Args:
            body: The function body

        Returns:
            Transformed function body
        """
        new_statements = []

        for stmt in body.body:
            # Skip the flag initialization statement (e.g., found = False)
            if self._is_flag_initialization(stmt):
                continue

            # Transform for loops to remove the guard clause
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
        new_body_statements = []

        for stmt in for_loop.body.body:
            # Transform if statements that guard with the control flag
            if isinstance(stmt, cst.If):
                transformed = self._transform_if_statement(stmt)
                # transformed can be a list of statements or a single statement or None
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
        # Check if this is the guard clause (e.g., if not found:)
        if self._is_guard_clause(if_stmt.test):
            # Extract the body of the guard clause and transform it
            return self._transform_guard_body(if_stmt.body)

        # Otherwise, transform the body to replace flag assignments with return
        new_body = self._replace_flag_assignments_with_return(if_stmt.body)
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
        # The guard body contains if statements that we need to extract and transform
        transformed_statements = []

        for stmt in body.body:
            if isinstance(stmt, cst.If):
                # Transform this if statement and add it to the list (no guard wrapper)
                new_body = self._replace_flag_assignments_with_return(stmt.body)
                transformed_statements.append(stmt.with_changes(body=new_body))
            else:
                # Keep other statements as-is
                transformed_statements.append(stmt)

        return transformed_statements

    def _replace_flag_assignments_with_return(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Replace flag assignments with return statements.

        Args:
            body: The body to transform

        Returns:
            Transformed body
        """
        new_statements = []

        for stmt in body.body:
            # Replace flag = True with return
            if isinstance(stmt, cst.SimpleStatementLine):
                replaced = False
                for s in stmt.body:
                    if isinstance(s, cst.Assign):
                        for target in s.targets:
                            if isinstance(target.target, cst.Name):
                                if target.target.value == self.flag_variable:
                                    # Replace with return statement
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
