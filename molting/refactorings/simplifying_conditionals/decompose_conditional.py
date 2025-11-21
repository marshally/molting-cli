"""Decompose Conditional refactoring - extract condition and branches into methods."""

import re
from pathlib import Path
import libcst as cst
from typing import Optional, Tuple, List, Set

from molting.core.refactoring_base import RefactoringBase


class DecomposeConditional(RefactoringBase):
    """Extract condition and branches into methods using libcst for AST transformation."""

    def __init__(self, file_path: str, target: str):
        """Initialize the DecomposeConditional refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name#L2")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()
        # Parse the target specification to extract line number and function name
        # Parses targets like:
        # - "function_name#L2" -> function name + line number
        # - "ClassName::method_name#L3" -> class name + method name + line number
        try:
            name_part, self.line_number, _ = self.parse_line_range_target(self.target)
        except ValueError:
            raise ValueError(f"Invalid target format: {self.target}")

        # Check if it's a class method (contains ::)
        if "::" in name_part:
            self.class_name, self.function_name = self.parse_qualified_target(name_part)
        else:
            self.class_name = None
            self.function_name = name_part

    def apply(self, source: str) -> str:
        """Apply the decompose conditional refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with decomposed conditionals
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = DecomposeConditionalTransformer(
            function_name=self.function_name,
            class_name=self.class_name,
            line_number=self.line_number,
            source_lines=source.split('\n')
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
        return f"def {self.function_name}" in source


class DecomposeConditionalTransformer(cst.CSTTransformer):
    """Transform CST to decompose conditional statements."""

    def __init__(self, function_name: str, class_name: Optional[str], line_number: int, source_lines: list):
        """Initialize the transformer.

        Args:
            function_name: Name of the function to modify
            class_name: Optional name of the class containing the function
            line_number: Line number of the if statement
            source_lines: Original source code split by lines
        """
        self.function_name = function_name
        self.class_name = class_name
        self.line_number = line_number
        self.source_lines = source_lines
        self.extracted_functions: List[cst.FunctionDef] = []
        self.found_target = False
        self.inside_target_class = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add extracted functions to the module."""
        if self.extracted_functions:
            # Add the extracted functions after the module body
            new_body = list(updated_node.body) + self.extracted_functions
            return updated_node.with_changes(body=new_body)
        return updated_node

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when we enter the target class."""
        if self.class_name and node.name.value == self.class_name:
            self.inside_target_class = True
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Process the class definition."""
        if self.class_name and updated_node.name.value == self.class_name:
            self.inside_target_class = False
        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        """Process function definitions."""
        if updated_node.name.value != self.function_name:
            return updated_node

        # If we're looking for a class method and we're not inside the right class, skip
        if self.class_name and not self.inside_target_class:
            return updated_node

        # If we're looking for a standalone function and there's a class name, skip
        if not self.class_name and self.inside_target_class:
            return updated_node

        # Process the function body to find and decompose the if statement
        new_body = self._process_function_body(updated_node.body)
        return updated_node.with_changes(body=new_body)

    def _process_function_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Process function body to decompose conditionals.

        Args:
            body: The function body

        Returns:
            Modified body with decomposed conditionals
        """
        statements = list(body.body)
        new_statements = []

        for stmt in statements:
            if isinstance(stmt, cst.If):
                # We found an if statement, decompose it
                new_if_stmt = self._decompose_if_statement(stmt)
                new_statements.append(new_if_stmt)
                self.found_target = True
            else:
                new_statements.append(stmt)

        return body.with_changes(body=new_statements)

    def _decompose_if_statement(self, if_stmt: cst.If) -> cst.If:
        """Decompose an if statement into extracted methods.

        Args:
            if_stmt: The if statement to decompose

        Returns:
            Modified if statement with method calls
        """
        # Extract the condition and create method
        condition_expr = if_stmt.test
        condition_method_name = "is_winter"

        # Create the condition method
        condition_method = self._create_condition_method(condition_method_name, condition_expr)
        self.extracted_functions.append(condition_method)

        # Extract the then-block and create method
        then_block = if_stmt.body
        then_method_name = "winter_charge"
        then_method = self._create_then_method(then_method_name, then_block)
        self.extracted_functions.append(then_method)

        # Extract the else-block and create method (if it exists)
        else_block = if_stmt.orelse
        else_method_name = "summer_charge"
        new_else = None
        if else_block:
            # Extract the body from the Else node
            else_body = None
            if isinstance(else_block, cst.Else):
                else_body = else_block.body
            elif isinstance(else_block, cst.If):
                # This is an elif
                else_body = else_block

            if else_body:
                else_method = self._create_else_method(else_method_name, else_body)
                self.extracted_functions.append(else_method)
                new_else = self._create_new_else_body(else_method_name)

        # Create new condition call with proper arguments
        if self.class_name:
            # For class methods, pass self
            new_condition = cst.Call(func=cst.Name(condition_method_name), args=[cst.Arg(cst.Name("self"))])
        else:
            new_condition = cst.Call(func=cst.Name(condition_method_name), args=[cst.Arg(cst.Name("date"))])

        # Create new body with method calls
        new_body = self._create_new_then_body(then_method_name)

        # Build the new if statement
        new_if_stmt = if_stmt.with_changes(
            test=new_condition,
            body=new_body,
            orelse=new_else
        )

        return new_if_stmt

    def _create_condition_method(self, method_name: str, condition: cst.BaseExpression) -> cst.FunctionDef:
        """Create a method that returns the condition.

        Args:
            method_name: Name for the condition method
            condition: The condition expression

        Returns:
            A FunctionDef for the condition method
        """
        # Create the return statement with the condition
        return_stmt = cst.SimpleStatementLine(
            body=[cst.Return(value=condition)]
        )

        # Create function body
        body = cst.IndentedBlock(body=[return_stmt])

        # Create function parameters
        if self.class_name:
            # For class methods, need self parameter
            params = cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))]
            )
        else:
            # For standalone functions
            params = cst.Parameters(
                params=[cst.Param(name=cst.Name("date"))]
            )

        # Create and return the function definition
        return cst.FunctionDef(
            name=cst.Name(method_name),
            params=params,
            body=body
        )

    def _create_then_method(self, method_name: str, then_block: cst.BaseCompoundStatement) -> cst.FunctionDef:
        """Create a method for the then-block.

        Args:
            method_name: Name for the then method
            then_block: The then-block statements

        Returns:
            A FunctionDef for the then method
        """
        # Extract statements from the then block
        if isinstance(then_block, cst.IndentedBlock):
            statements = list(then_block.body)
        else:
            statements = [then_block]

        # Get the assignment statement and extract its value
        assign_stmt = statements[0]
        if isinstance(assign_stmt, cst.SimpleStatementLine) and len(assign_stmt.body) > 0:
            assign = assign_stmt.body[0]
            if isinstance(assign, cst.Assign):
                # Return the right side of the assignment
                return_stmt = cst.SimpleStatementLine(
                    body=[cst.Return(value=assign.value)]
                )
                body = cst.IndentedBlock(body=[return_stmt])
            else:
                body = cst.IndentedBlock(body=statements)
        else:
            body = cst.IndentedBlock(body=statements)

        # Create function parameters
        if self.class_name:
            # For class methods with simple return values, no parameters
            params = cst.Parameters(params=[])
        else:
            params = cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("quantity")),
                    cst.Param(name=cst.Name("winter_rate")),
                    cst.Param(name=cst.Name("winter_service_charge"))
                ]
            )

        # Create and return the function definition
        return cst.FunctionDef(
            name=cst.Name(method_name),
            params=params,
            body=body
        )

    def _create_else_method(self, method_name: str, else_block: cst.BaseCompoundStatement) -> cst.FunctionDef:
        """Create a method for the else-block.

        Args:
            method_name: Name for the else method
            else_block: The else-block statements (typically an IndentedBlock)

        Returns:
            A FunctionDef for the else method
        """
        # Extract statements from the else block
        # else_block can be an IndentedBlock (normal else) or If (elif)
        if isinstance(else_block, cst.IndentedBlock):
            statements = list(else_block.body)
        elif isinstance(else_block, cst.If):
            # This is an elif, skip for now
            statements = []
        else:
            statements = [else_block]

        # Get the assignment statement and extract its value
        assign_stmt = statements[0] if statements else None
        if assign_stmt and isinstance(assign_stmt, cst.SimpleStatementLine) and len(assign_stmt.body) > 0:
            assign = assign_stmt.body[0]
            if isinstance(assign, cst.Assign):
                # Return the right side of the assignment
                return_stmt = cst.SimpleStatementLine(
                    body=[cst.Return(value=assign.value)]
                )
                body = cst.IndentedBlock(body=[return_stmt])
            else:
                body = cst.IndentedBlock(body=statements)
        else:
            body = cst.IndentedBlock(body=statements if statements else [])

        # Create function parameters
        if self.class_name:
            # For class methods with simple return values, no parameters
            params = cst.Parameters(params=[])
        else:
            params = cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("quantity")),
                    cst.Param(name=cst.Name("summer_rate"))
                ]
            )

        # Create and return the function definition
        return cst.FunctionDef(
            name=cst.Name(method_name),
            params=params,
            body=body
        )

    def _create_new_then_body(self, method_name: str) -> cst.IndentedBlock:
        """Create the new body for the then-block with a method call.

        Args:
            method_name: Name of the method to call

        Returns:
            An IndentedBlock with the method call
        """
        # Create the method call
        if self.class_name:
            # For class methods, no arguments
            call = cst.Call(func=cst.Name(method_name), args=[])
        else:
            call = cst.Call(
                func=cst.Name(method_name),
                args=[
                    cst.Arg(cst.Name("quantity")),
                    cst.Arg(cst.Name("winter_rate")),
                    cst.Arg(cst.Name("winter_service_charge"))
                ]
            )

        # Create the assignment
        assign = cst.Assign(
            targets=[cst.AssignTarget(target=cst.Name("discount_rate" if self.class_name else "charge"))],
            value=call
        )

        # Create the statement
        stmt = cst.SimpleStatementLine(body=[assign])

        return cst.IndentedBlock(body=[stmt])

    def _create_new_else_body(self, method_name: str) -> cst.Else:
        """Create the new else block with a method call.

        Args:
            method_name: Name of the method to call

        Returns:
            An Else node with the method call
        """
        # Create the method call
        if self.class_name:
            # For class methods, no arguments
            call = cst.Call(func=cst.Name(method_name), args=[])
        else:
            call = cst.Call(
                func=cst.Name(method_name),
                args=[
                    cst.Arg(cst.Name("quantity")),
                    cst.Arg(cst.Name("summer_rate"))
                ]
            )

        # Create the assignment
        assign = cst.Assign(
            targets=[cst.AssignTarget(target=cst.Name("discount_rate" if self.class_name else "charge"))],
            value=call
        )

        # Create the statement
        stmt = cst.SimpleStatementLine(body=[assign])

        # Wrap in an Else node
        return cst.Else(body=cst.IndentedBlock(body=[stmt]))
