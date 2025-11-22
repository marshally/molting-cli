"""Base classes for refactoring operations."""

from abc import ABC, abstractmethod


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
