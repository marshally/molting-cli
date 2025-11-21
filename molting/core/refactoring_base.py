"""Base classes for refactoring operations."""

import re
from abc import ABC, abstractmethod
from typing import Any, Tuple


class RefactoringBase(ABC):
    """Base class for all refactoring operations."""

    @abstractmethod
    def apply(self, source: str) -> str:
        """Apply the refactoring to the given source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code
        """
        pass

    @abstractmethod
    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        pass

    def parse_line_range_target(self, target: str) -> Tuple[str, int, int]:
        """Parse target specification with line range information.

        Parses targets like:
        - "Order::print_owing#L9-L11" -> class/method + start and end line
        - "Order::print_owing#L9" -> class/method + single line (start == end)
        - "calculate#L5-L7" -> function + line range
        - "function#L5" -> function + single line

        Args:
            target: Target specification string

        Returns:
            Tuple of (method_spec, start_line, end_line)

        Raises:
            ValueError: If target format is invalid
        """
        # Pattern: optional_class::optional_method#L{start}-L{end} or #L{start}
        pattern = r'^(.+?)#L(\d+)(?:-L(\d+))?$'
        match = re.match(pattern, target)

        if not match:
            raise ValueError(f"Invalid target format: {target}")

        method_spec = match.group(1)  # e.g., "Order::print_owing" or "calculate"
        start_line = int(match.group(2))
        end_line = int(match.group(3)) if match.group(3) else start_line

        return method_spec, start_line, end_line
