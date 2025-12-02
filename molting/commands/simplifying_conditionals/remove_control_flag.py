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

        # Parse target as function_name::flag_variable or ClassName::method_name::flag_variable
        parts = target.split("::")
        if len(parts) < 2:
            raise ValueError(
                f"Invalid target format: {target}. "
                "Expected: function_name::flag_variable or ClassName::function_name::flag_variable"
            )

        if len(parts) == 2:
            # Module-level function: function_name::flag_variable
            class_name = ""
            function_name = parts[0]
            flag_variable = parts[1]
        else:
            # Class method: ClassName::function_name::flag_variable
            class_name = parts[0]
            function_name = parts[1]
            flag_variable = parts[2]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = RemoveControlFlagTransformer(class_name, function_name, flag_variable)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class RemoveControlFlagTransformer(cst.CSTTransformer):
    """Transforms a function by removing control flag and using return/break."""

    def __init__(self, class_name: str, function_name: str, flag_variable: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class (empty string for module-level functions)
            function_name: Name of the function to transform
            flag_variable: Name of the control flag variable to remove
        """
        self.class_name = class_name
        self.function_name = function_name
        self.flag_variable = flag_variable
        self.current_class: str | None = None
        self.initial_flag_value: bool = False  # Track the initial flag value
        self.has_return_not_flag: bool = False  # Track if there's a return not flag stmt

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
        """Leave function definition and remove control flag pattern."""
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
        """Transform the function body to remove control flag.

        Args:
            body: The function body

        Returns:
            Transformed function body
        """
        # First pass: extract the final return statement value (if it's not a flag-based return)
        found_return = False
        for stmt in reversed(body.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                for s in stmt.body:
                    if isinstance(s, cst.Return) and s.value is not None:
                        # Only use this if it's not a "return not flag" statement
                        if not self._is_return_not_flag(stmt):
                            self.final_return_value = s.value
                            found_return = True
                            break
                if found_return:
                    break

        # Second pass: check if there's a return not flag statement
        for stmt in body.body:
            if self._is_return_not_flag(stmt):
                self.has_return_not_flag = True
                break

        new_statements: list[cst.BaseStatement] = []

        for stmt in body.body:
            if self._is_flag_initialization(stmt):
                continue

            if isinstance(stmt, cst.For):
                new_for = self._transform_for_loop(stmt)
                new_statements.append(new_for)
            elif self._is_return_not_flag(stmt):
                # Transform "return not found" to "return True" (if initial was False)
                # or "return False" (if initial was True)
                return_value = "True" if not self.initial_flag_value else "False"
                new_statements.append(
                    cst.SimpleStatementLine(body=[cst.Return(value=cst.Name(return_value))])
                )
            else:
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)

    def _is_return_not_flag(self, stmt: cst.BaseStatement) -> bool:
        """Check if statement is 'return not flag_variable'.

        Args:
            stmt: Statement to check

        Returns:
            True if this is a return not flag_variable statement
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        for s in stmt.body:
            if isinstance(s, cst.Return) and s.value is not None:
                if isinstance(s.value, cst.UnaryOperation):
                    if isinstance(s.value.operator, cst.Not):
                        if isinstance(s.value.expression, cst.Name):
                            return s.value.expression.value == self.flag_variable
        return False

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
                    # Track the initial value
                    if isinstance(s.value, cst.Name):
                        self.initial_flag_value = s.value.value == "True"
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

    def _contains_flag_reference(self, test: cst.BaseExpression) -> bool:
        """Check if test expression contains a reference to the flag variable.

        Args:
            test: The test expression

        Returns:
            True if the expression contains the flag variable
        """
        if isinstance(test, cst.UnaryOperation) and isinstance(test.operator, cst.Not):
            if (
                isinstance(test.expression, cst.Name)
                and test.expression.value == self.flag_variable
            ):
                return True
        if isinstance(test, cst.BooleanOperation):
            return self._contains_flag_reference(test.left) or self._contains_flag_reference(
                test.right
            )
        return False

    def _remove_flag_reference(self, test: cst.BaseExpression) -> cst.BaseExpression | None:
        """Remove flag references from a test expression.

        Args:
            test: The test expression

        Returns:
            The expression with flag references removed, or None if the entire
            expression was the flag
        """
        if isinstance(test, cst.UnaryOperation) and isinstance(test.operator, cst.Not):
            if (
                isinstance(test.expression, cst.Name)
                and test.expression.value == self.flag_variable
            ):
                return None

        if isinstance(test, cst.BooleanOperation):
            if isinstance(test.operator, cst.And):
                # For AND, remove the flag part
                left = self._remove_flag_reference(test.left)
                right = self._remove_flag_reference(test.right)
                if left is None:
                    return right
                if right is None:
                    return left
                return cst.BooleanOperation(left=left, operator=test.operator, right=right)
            elif isinstance(test.operator, cst.Or):
                # For OR, we can't easily simplify, so keep it for now
                left = self._remove_flag_reference(test.left)
                right = self._remove_flag_reference(test.right)
                if left is None:
                    return right
                if right is None:
                    return left
                return cst.BooleanOperation(left=left, operator=test.operator, right=right)

        return test

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
                # Check if the condition contains a flag reference and remove it
                if self._contains_flag_reference(stmt.test):
                    new_test = self._remove_flag_reference(stmt.test)
                    if new_test is not None:
                        # Keep the if statement but with the cleaned condition
                        if_body = cast(cst.IndentedBlock, stmt.body)
                        new_body = self._replace_flag_assignments_with_return(if_body)
                        transformed_statements.append(
                            stmt.with_changes(test=new_test, body=new_body)
                        )
                    else:
                        # The entire condition was the flag check, unwrap the body
                        if_body = cast(cst.IndentedBlock, stmt.body)
                        new_body = self._replace_flag_assignments_with_return(if_body)
                        transformed_statements.extend(new_body.body)
                else:
                    # No flag reference, just transform the body
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
                        # Use the final return value if there is one
                        if getattr(self, "final_return_value", None) is not None:
                            new_statements.append(
                                cst.SimpleStatementLine(
                                    body=[cst.Return(value=self.final_return_value)]
                                )
                            )
                        elif self.has_return_not_flag:
                            # Determine what value is being assigned to the flag
                            assigned_value = True
                            if isinstance(s.value, cst.Name):
                                assigned_value = s.value.value == "True"
                            # Return the opposite since the original code did "return not flag"
                            return_value = "False" if assigned_value else "True"
                            new_statements.append(
                                cst.SimpleStatementLine(
                                    body=[cst.Return(value=cst.Name(return_value))]
                                )
                            )
                        else:
                            # No return value for simple exit-only case
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
