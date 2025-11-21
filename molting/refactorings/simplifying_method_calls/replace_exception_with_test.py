"""Replace Exception with Test refactoring - use explicit condition checks instead of try-except."""

from pathlib import Path
from typing import Optional, Sequence

import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class ReplaceExceptionWithTest(RefactoringBase):
    """Replace exception handling with explicit condition checks."""

    def __init__(self, file_path: str, target: str, source_code: Optional[str] = None):
        """Initialize the ReplaceExceptionWithTest refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function name (e.g., "get_value_for_period" or with line range)
            source_code: Source code to refactor (optional, will read from file if not provided)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = source_code if source_code is not None else self.file_path.read_text()

        # Parse the target - can be just function name or with line ranges
        if "#L" in target:
            self.func_name, self.start_line, self.end_line = self.parse_line_range_target(target)
        else:
            self.func_name = target
            self.start_line = None
            self.end_line = None

    def apply(self, source: str) -> str:
        """Apply the replace exception with test refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with exception replaced with test
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ReplaceExceptionWithTestTransformer(
            func_name=self.func_name,
            start_line=self.start_line,
            end_line=self.end_line,
        )
        modified_tree = tree.visit(transformer)

        if not transformer.modified:
            raise ValueError(f"Could not find target: {self.target}")

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = cst.parse_module(source)
            validator = ValidateReplaceExceptionWithTestTransformer(
                func_name=self.func_name,
                start_line=self.start_line,
                end_line=self.end_line,
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class ReplaceExceptionWithTestTransformer(cst.CSTTransformer):
    """Transform try-except blocks to use explicit condition checks."""

    def __init__(
        self,
        func_name: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ):
        """Initialize the transformer.

        Args:
            func_name: Name of the function to transform
            start_line: Start line of try block (optional)
            end_line: End line of try block (optional)
        """
        self.func_name = func_name
        self.start_line = start_line
        self.end_line = end_line
        self.inside_target_function = False
        self.modified = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Track entry into function definitions."""
        if node.name.value == self.func_name:
            self.inside_target_function = True
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Track exit from function definitions."""
        if original_node.name.value == self.func_name:
            self.inside_target_function = False
        return updated_node

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.IndentedBlock:
        """Process function body and replace try-except blocks."""
        if not self.inside_target_function:
            return updated_node

        # Process the body to find and replace try-except blocks
        new_body = []
        for stmt in updated_node.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                new_body.append(stmt)
            elif isinstance(stmt, cst.Try):
                # Check if this is a try-except IndexError pattern
                transformed = self._transform_try_except(stmt)
                if transformed is not None:
                    new_body.extend(transformed)
                    self.modified = True
                else:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        return updated_node.with_changes(body=new_body)

    def _transform_try_except(
        self, try_stmt: cst.Try
    ) -> Optional[Sequence[cst.BaseCompoundStatement]]:
        """Transform a try-except IndexError block into if-else."""
        # Check if this try block has an IndexError handler
        index_error_handler = None
        for handler in try_stmt.handlers:
            if handler.type is not None and self._is_index_error(handler.type):
                index_error_handler = handler
                break

        if index_error_handler is None:
            return None

        # Pattern: try: return values[index]; except IndexError: return 0
        # Transform to: if index >= len(values): return 0; return values[index]

        # Extract information from try body
        try_body_stmts = list(try_stmt.body.body)
        if not try_body_stmts:
            return None

        # Find the return statement in try block
        try_return_stmt = None
        for stmt in try_body_stmts:
            if isinstance(stmt, cst.SimpleStatementLine):
                for inner in stmt.body:
                    if isinstance(inner, cst.Return):
                        try_return_stmt = stmt
                        break

        if try_return_stmt is None:
            return None

        # Find the return statement in except handler
        except_return_stmt = None
        for stmt in index_error_handler.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for inner in stmt.body:
                    if isinstance(inner, cst.Return):
                        except_return_stmt = stmt
                        break

        if except_return_stmt is None:
            return None

        # Extract subscript info from try return
        subscript_info = self._extract_subscript_info_from_return(try_return_stmt)
        if subscript_info is None:
            return None

        container_name, index_name = subscript_info

        # Build the condition: index >= len(container)
        condition = cst.ComparisonTarget(
            operator=cst.GreaterThanEqual(),
            comparator=cst.Call(
                func=cst.Name("len"),
                args=[cst.Arg(cst.Name(container_name))],
            ),
        )
        comparison = cst.Comparison(left=cst.Name(index_name), comparisons=[condition])

        # Create the if statement WITHOUT else - return in except handler, then normal return
        if_stmt = cst.If(
            test=comparison,
            body=cst.IndentedBlock(body=[except_return_stmt]),
        )

        # Return both the if statement and the original try return statement
        return [if_stmt, try_return_stmt]

    def _is_index_error(self, exception_type: cst.BaseExpression) -> bool:
        """Check if the exception type is IndexError."""
        if isinstance(exception_type, cst.Name):
            return exception_type.value == "IndexError"
        return False

    def _extract_subscript_info_from_return(
        self, return_stmt: cst.SimpleStatementLine
    ) -> Optional[tuple]:
        """Extract container and index from a return statement with subscript."""
        for stmt in return_stmt.body:
            if isinstance(stmt, cst.Return) and stmt.value:
                if isinstance(stmt.value, cst.Subscript):
                    if isinstance(stmt.value.value, cst.Name):
                        container = stmt.value.value.value
                        # Extract the index
                        if stmt.value.slice and len(stmt.value.slice) > 0:
                            index_slice = stmt.value.slice[0]
                            if isinstance(index_slice, cst.SubscriptElement):
                                slice_value = index_slice.slice
                                if isinstance(slice_value, cst.Index):
                                    if isinstance(slice_value.value, cst.Name):
                                        index = slice_value.value.value
                                        return (container, index)
        return None


class ValidateReplaceExceptionWithTestTransformer(cst.CSTVisitor):
    """Visitor to check if the target function exists."""

    def __init__(
        self, func_name: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ):
        """Initialize the validator.

        Args:
            func_name: Name of the function to find
            start_line: Start line (optional)
            end_line: End line (optional)
        """
        self.func_name = func_name
        self.start_line = start_line
        self.end_line = end_line
        self.found = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Check if this is the target function."""
        if node.name.value == self.func_name:
            self.found = True
        return True
