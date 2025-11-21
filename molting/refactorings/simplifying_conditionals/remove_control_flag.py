"""Remove Control Flag refactoring - replace control flag variables with break or return statements."""

import re
from pathlib import Path
from typing import Optional

import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class RemoveControlFlag(RefactoringBase):
    """Replace control flag variables with break or return statements using libcst."""

    def __init__(self, file_path: str, target: str):
        """Initialize the RemoveControlFlag refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name::flag_name" or "ClassName::method_name::flag_name")

        Raises:
            ValueError: If target format is invalid
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()
        # Parse the target specification to extract class name, function name, and flag name.
        # Parses targets like:
        # - "function_name::flag_name" -> function name + flag name
        # - "ClassName::method_name::flag_name" -> class name + method name + flag name
        parts = self.target.split("::")

        if len(parts) == 2:
            # function_name::flag_name
            self.function_name = parts[0]
            self.flag_name = parts[1]
            self.class_name = None
        elif len(parts) == 3:
            # ClassName::method_name::flag_name - use parse_qualified_target for first two parts
            self.class_name, self.function_name = self.parse_qualified_target(f"{parts[0]}::{parts[1]}")
            self.flag_name = parts[2]
        else:
            raise ValueError(f"Invalid target format: {self.target}")

    def apply(self, source: str) -> str:
        """Apply the remove control flag refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with control flags removed

        Raises:
            ValueError: If the source code cannot be parsed or refactoring cannot be applied
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = RemoveControlFlagTransformer(
            function_name=self.function_name,
            class_name=self.class_name,
            flag_name=self.flag_name
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
        # Check that the function exists
        return f"def {self.function_name}" in source and self.flag_name in source


class RemoveControlFlagTransformer(cst.CSTTransformer):
    """Transform CST to remove control flag variables."""

    def __init__(self, function_name: str, class_name: Optional[str], flag_name: str):
        """Initialize the transformer.

        Args:
            function_name: Name of the function to modify
            class_name: Optional name of the class containing the function
            flag_name: Name of the control flag variable
        """
        self.function_name = function_name
        self.class_name = class_name
        self.flag_name = flag_name
        self.inside_target_class = False
        self.inside_target_function = False
        self.has_return_in_function = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when we enter the target class."""
        if self.class_name and node.name.value == self.class_name:
            self.inside_target_class = True
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Track when we leave the target class."""
        if self.class_name and updated_node.name.value == self.class_name:
            self.inside_target_class = False
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Track when we enter the target function."""
        if node.name.value == self.function_name:
            # If we're looking for a class method and we're inside the right class, mark it
            if self.class_name and self.inside_target_class:
                self.inside_target_function = True
                self.has_return_in_function = self._check_for_return(node.body)
            # If we're looking for a standalone function and not inside a class, mark it
            elif not self.class_name and not self.inside_target_class:
                self.inside_target_function = True
                self.has_return_in_function = self._check_for_return(node.body)
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Process function definitions."""
        if updated_node.name.value == self.function_name:
            if (self.class_name and self.inside_target_class) or (not self.class_name and not self.inside_target_class):
                # We're in the target function - process its body
                new_body = self._process_function_body(updated_node.body)
                self.inside_target_function = False
                return updated_node.with_changes(body=new_body)

        return updated_node

    def _check_for_return(self, body: cst.IndentedBlock) -> bool:
        """Check if function body contains a return statement."""
        for stmt in body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.Return):
                        return True
        return False

    def _process_function_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Process function body to remove control flag.

        Args:
            body: The function body to process

        Returns:
            Modified function body
        """
        statements = list(body.body)
        new_statements = []
        flag_init_value = None

        # First pass: find and remove flag initialization, capture its value
        for i, stmt in enumerate(statements):
            if self._is_flag_initialization(stmt):
                # Extract the initial value before removing
                flag_init_value = self._extract_flag_init_value(stmt)
                # Skip the flag initialization statement
                continue
            elif self._is_return_flag_statement(stmt):
                # Replace "return flag_name" with "return flag_init_value"
                if flag_init_value is None:
                    flag_init_value = cst.Name("False")
                return_stmt = cst.SimpleStatementLine(
                    body=[cst.Return(value=flag_init_value)]
                )
                new_statements.append(return_stmt)
            else:
                # Process the statement to replace flag checks and assignments
                processed_stmt = self._process_statement(stmt)
                new_statements.append(processed_stmt)

        return body.with_changes(body=new_statements)

    def _is_flag_initialization(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is the flag variable initialization."""
        if isinstance(stmt, cst.SimpleStatementLine):
            for item in stmt.body:
                if isinstance(item, cst.Assign):
                    for target in item.targets:
                        if isinstance(target.target, cst.Name):
                            if target.target.value == self.flag_name:
                                return True
        return False

    def _extract_flag_init_value(self, stmt: cst.BaseStatement) -> Optional[cst.BaseExpression]:
        """Extract the initial value from a flag initialization statement."""
        if isinstance(stmt, cst.SimpleStatementLine):
            for item in stmt.body:
                if isinstance(item, cst.Assign):
                    for target in item.targets:
                        if isinstance(target.target, cst.Name):
                            if target.target.value == self.flag_name:
                                return item.value
        return None

    def _is_return_flag_statement(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is 'return flag_name'."""
        if isinstance(stmt, cst.SimpleStatementLine):
            for item in stmt.body:
                if isinstance(item, cst.Return):
                    if isinstance(item.value, cst.Name):
                        if item.value.value == self.flag_name:
                            return True
        return False

    def _get_flag_init_value(self, statements: list) -> Optional[cst.BaseExpression]:
        """Get the initial value of the flag variable for the default return."""
        for stmt in statements:
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.Assign):
                        for target in item.targets:
                            if isinstance(target.target, cst.Name):
                                if target.target.value == self.flag_name:
                                    # Return the initial value (not the opposite)
                                    # If flag initialized to False, return False
                                    # If flag initialized to True, return True
                                    if isinstance(item.value, cst.Name):
                                        return item.value
                                    else:
                                        # For non-name values, return False by default
                                        return cst.Name("False")
        return cst.Name("False")

    def _ends_with_return(self, statements: list) -> bool:
        """Check if statement list ends with a return statement."""
        if not statements:
            return False
        last_stmt = statements[-1]
        if isinstance(last_stmt, cst.SimpleStatementLine):
            for item in last_stmt.body:
                if isinstance(item, cst.Return):
                    return True
        return False

    def _process_statement(self, stmt: cst.BaseStatement) -> cst.BaseStatement:
        """Process a statement to remove flag checks and replace assignments.

        Args:
            stmt: The statement to process

        Returns:
            Modified statement
        """
        if isinstance(stmt, cst.For):
            return self._process_for_loop(stmt)
        elif isinstance(stmt, cst.While):
            return self._process_while_loop(stmt)
        elif isinstance(stmt, cst.If):
            return self._process_if_statement(stmt)
        else:
            return stmt

    def _process_for_loop(self, loop: cst.For) -> cst.For:
        """Process a for loop to handle flag assignments and checks.

        Args:
            loop: The for loop to process

        Returns:
            Modified for loop
        """
        new_body = list(loop.body.body)
        processed_body = []

        for stmt in new_body:
            processed = self._process_loop_statement(stmt)
            if isinstance(processed, RemoveControlFlagTransformer._UnwrapMarker):
                # Unwrap the marker statements
                processed_body.extend(processed.statements)
            else:
                processed_body.append(processed)

        return loop.with_changes(body=loop.body.with_changes(body=processed_body))

    def _process_while_loop(self, loop: cst.While) -> cst.While:
        """Process a while loop to handle flag assignments and checks.

        Args:
            loop: The while loop to process

        Returns:
            Modified while loop
        """
        new_body = list(loop.body.body)
        processed_body = []

        for stmt in new_body:
            processed = self._process_loop_statement(stmt)
            processed_body.append(processed)

        return loop.with_changes(body=loop.body.with_changes(body=processed_body))

    def _process_loop_statement(self, stmt: cst.BaseStatement) -> cst.BaseStatement:
        """Process a statement inside a loop.

        Args:
            stmt: The statement to process

        Returns:
            Modified statement or tuple of statements if unwrapping
        """
        if isinstance(stmt, cst.If):
            # Check if this is a flag check (if not flag_name or if flag_name)
            if self._is_flag_check(stmt.test):
                # This is a flag check - we need to unwrap its body
                # Return a marker that will be unwrapped by the caller
                new_body = list(stmt.body.body)
                processed_body = []
                for inner_stmt in new_body:
                    processed = self._process_flag_assignment(inner_stmt)
                    processed_body.append(processed)
                # Return special marker object to indicate unwrapping
                return RemoveControlFlagTransformer._UnwrapMarker(processed_body)
            else:
                # Process nested if statements
                new_body = list(stmt.body.body)
                processed_body = []
                for inner_stmt in new_body:
                    processed = self._process_flag_assignment(inner_stmt)
                    if isinstance(processed, RemoveControlFlagTransformer._UnwrapMarker):
                        # Unwrap the marker
                        processed_body.extend(processed.statements)
                    else:
                        processed_body.append(processed)

                new_stmt = stmt.with_changes(body=stmt.body.with_changes(body=processed_body))

                # Also process else clause if present
                if stmt.orelse:
                    new_else = self._process_else(stmt.orelse)
                    new_stmt = new_stmt.with_changes(orelse=new_else)

                return new_stmt
        else:
            return self._process_flag_assignment(stmt)

    class _UnwrapMarker:
        """Marker class for statements that should be unwrapped."""
        def __init__(self, statements):
            self.statements = statements

    def _is_flag_check(self, test: cst.BaseExpression) -> bool:
        """Check if an expression is a flag check (not flag_name or flag_name)."""
        if isinstance(test, cst.UnaryOperation):
            if isinstance(test.operator, cst.Not):
                if isinstance(test.expression, cst.Name):
                    return test.expression.value == self.flag_name
        elif isinstance(test, cst.Name):
            return test.value == self.flag_name
        elif isinstance(test, cst.Comparison):
            # Handle comparisons like "flag == False"
            if isinstance(test.left, cst.Name) and test.left.value == self.flag_name:
                return True
        return False

    def _remove_flag_check(self, if_stmt: cst.If) -> cst.If:
        """Remove a flag check from an if statement.

        Args:
            if_stmt: The if statement with flag check

        Returns:
            Modified if statement without flag check, or the inner statements
        """
        # Process the body to replace flag assignments
        new_body = list(if_stmt.body.body)
        processed_body = []
        for stmt in new_body:
            processed = self._process_flag_assignment(stmt)
            processed_body.append(processed)

        # Return the if statement with the flag check removed and body updated
        # We return the body statements directly as a placeholder
        # This will be handled by the parent context
        new_if = if_stmt.with_changes(
            test=cst.Name("True"),  # Replace with always-true condition
            body=if_stmt.body.with_changes(body=processed_body)
        )
        return new_if

    def _process_flag_assignment(self, stmt: cst.BaseStatement) -> cst.BaseStatement:
        """Process a statement to replace flag assignments with return/break.

        Args:
            stmt: The statement to process

        Returns:
            Modified statement
        """
        if isinstance(stmt, cst.If):
            new_body = list(stmt.body.body)
            processed_body = []
            for inner_stmt in new_body:
                processed = self._process_flag_assignment(inner_stmt)
                processed_body.append(processed)

            new_stmt = stmt.with_changes(body=stmt.body.with_changes(body=processed_body))

            # Also process else clause if present
            if stmt.orelse:
                new_else = self._process_else(stmt.orelse)
                new_stmt = new_stmt.with_changes(orelse=new_else)

            return new_stmt
        elif isinstance(stmt, cst.SimpleStatementLine):
            # Check if this is a flag assignment
            new_body = []
            for item in stmt.body:
                if isinstance(item, cst.Assign):
                    if self._is_flag_assignment(item):
                        # Replace with return statement
                        return_stmt = self._create_return_from_assignment(item)
                        return cst.SimpleStatementLine(body=[return_stmt])
                new_body.append(item)
            return stmt.with_changes(body=new_body)
        else:
            return stmt

    def _is_flag_assignment(self, assign: cst.Assign) -> bool:
        """Check if an assignment is to the control flag."""
        for target in assign.targets:
            if isinstance(target.target, cst.Name):
                if target.target.value == self.flag_name:
                    return True
        return False

    def _create_return_from_assignment(self, assign: cst.Assign) -> cst.Return:
        """Create a return statement from a flag assignment.

        Args:
            assign: The assignment statement

        Returns:
            A return statement with the assigned value
        """
        # Return the value being assigned to the flag
        return cst.Return(value=assign.value)

    def _process_else(self, orelse: cst.BaseCompoundStatement) -> cst.BaseCompoundStatement:
        """Process an else clause to remove flag references.

        Args:
            orelse: The else clause (Else or If for elif)

        Returns:
            Modified else clause
        """
        if isinstance(orelse, cst.Else):
            new_body = list(orelse.body.body)
            processed_body = []
            for stmt in new_body:
                processed = self._process_flag_assignment(stmt)
                processed_body.append(processed)
            return orelse.with_changes(body=orelse.body.with_changes(body=processed_body))
        elif isinstance(orelse, cst.If):
            # This is an elif
            return self._process_if_statement(orelse)
        return orelse

    def _process_if_statement(self, if_stmt: cst.If) -> cst.If:
        """Process an if statement to remove flag references.

        Args:
            if_stmt: The if statement to process

        Returns:
            Modified if statement
        """
        # Process body
        new_body = list(if_stmt.body.body)
        processed_body = []
        for stmt in new_body:
            processed = self._process_flag_assignment(stmt)
            processed_body.append(processed)

        new_stmt = if_stmt.with_changes(body=if_stmt.body.with_changes(body=processed_body))

        # Process else if present
        if if_stmt.orelse:
            new_else = self._process_else(if_stmt.orelse)
            new_stmt = new_stmt.with_changes(orelse=new_else)

        return new_stmt
