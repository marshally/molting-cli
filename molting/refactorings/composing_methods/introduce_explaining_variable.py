"""Introduce Explaining Variable refactoring - extract complex expressions into named variables."""

import re
from pathlib import Path
from typing import Sequence, Union
import libcst as cst
from libcst import matchers as m

from molting.core.refactoring_base import RefactoringBase


class _IntroduceExplainingVariableTransformer(cst.CSTTransformer):
    """Transformer to introduce explaining variables by extracting expressions."""

    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(
        self,
        target_line: int,
        func_name: str,
        variable_name: str,
        expression: str = None,
        source_code: str = None
    ):
        """Initialize the transformer.

        Args:
            target_line: Line number to target (1-indexed)
            func_name: Name of the function to transform
            variable_name: Name for the new variable
            expression: The expression to extract
            source_code: Full source code for line extraction
        """
        self.target_line = target_line
        self.func_name = func_name
        self.variable_name = variable_name
        self.expression = expression
        self.source_code = source_code or ""
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

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> Union[cst.SimpleStatementLine, cst.FlattenSentinel]:
        """Handle return statements at the target line."""
        if not self.inside_target_function or self.modified:
            return updated_node

        # Check if this is a return statement
        if len(updated_node.body) > 0 and isinstance(updated_node.body[0], cst.Return):
            try:
                pos = self.get_metadata(cst.metadata.PositionProvider, original_node)
                if pos and pos.start.line <= self.target_line <= pos.end.line:
                    # Target line is within this return statement
                    return_stmt = updated_node.body[0]
                    if return_stmt.value is not None:
                        # Extract the target sub-expression
                        extracted_value = return_stmt.value

                        # Create the variable assignment
                        var_assignment = cst.SimpleStatementLine(
                            body=[
                                cst.Assign(
                                    targets=[cst.AssignTarget(target=cst.Name(self.variable_name))],
                                    value=extracted_value
                                )
                            ]
                        )
                        # Create new return statement with the variable
                        new_return = cst.SimpleStatementLine(
                            body=[cst.Return(value=cst.Name(self.variable_name))]
                        )
                        self.modified = True
                        # Return both statements
                        return cst.FlattenSentinel([var_assignment, new_return])
            except KeyError:
                # Metadata not available, skip
                pass

        return updated_node


class IntroduceExplainingVariable(RefactoringBase):
    """Extract complex expressions into named variables for improved readability."""

    def __init__(self, file_path: str, target: str, name: str, expression: str = None):
        """Initialize the Introduce Explaining Variable refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name#L10" or "ClassName::method_name#L10")
            name: Name for the new explaining variable
            expression: The expression to extract (optional, can be auto-detected)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.variable_name = name  # Store as variable_name internally
        self.expression = expression
        self.source = self.file_path.read_text()
        self._parse_target()

    def _parse_target(self) -> None:
        """Parse the target specification to extract function and line information.

        Parses targets like:
        - "function_name#L10" -> function + line number
        - "ClassName::method_name#L10" -> class::method + line number

        Raises:
            ValueError: If target format is invalid
        """
        # Pattern: optional_class::optional_func#L{line}
        pattern = r'^(.+?)#L(\d+)$'
        match = re.match(pattern, self.target)

        if not match:
            raise ValueError(f"Invalid target format: {self.target}. Expected format: 'function_name#L10' or 'ClassName::method_name#L10'")

        # Extract the function/method specification
        full_spec = match.group(1)  # e.g., "ClassName::method_name" or "function_name"
        self.start_line = int(match.group(2))

        # Extract the function name (the part after :: if present, otherwise the whole spec)
        if "::" in full_spec:
            self.func_name = full_spec.split("::")[-1]
        else:
            self.func_name = full_spec

    def apply(self, source: str) -> str:
        """Apply the introduce explaining variable refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with extracted variable
        """
        # Update source for this apply call
        self.source = source

        # Parse the source code
        module = cst.parse_module(source)

        # Use a transformer to apply the changes
        transformer = _IntroduceExplainingVariableTransformer(
            target_line=self.start_line,
            func_name=self.func_name,
            variable_name=self.variable_name,
            expression=self.expression,
            source_code=source
        )

        # Use metadata-based visiting
        wrapper = cst.metadata.MetadataWrapper(module)
        modified_module = wrapper.visit(transformer)
        return modified_module.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        lines = source.split('\n')
        # Check that the line number is within bounds
        return 1 <= self.start_line <= len(lines)
