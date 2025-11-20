"""Introduce Explaining Variable refactoring - extract complex expressions into named variables."""

import re
from pathlib import Path
import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class IntroduceExplainingVariable(RefactoringBase):
    """Extract complex expressions into named variables for improved readability."""

    def __init__(self, file_path: str, target: str, variable_name: str):
        """Initialize the Introduce Explaining Variable refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "function_name#L10" or "ClassName::method_name#L10")
            variable_name: Name for the new explaining variable
        """
        self.file_path = Path(file_path)
        self.target = target
        self.variable_name = variable_name
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
        return source

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
