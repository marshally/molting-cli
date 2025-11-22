"""Base class for all refactoring commands."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseCommand(ABC):
    """Base class for all refactoring commands."""

    name: str  # e.g., "rename-method"

    def __init__(self, file_path: Path, **params: Any):
        """Initialize the command.

        Args:
            file_path: Path to the file to refactor
            **params: Additional parameters for the refactoring
        """
        self.file_path = file_path
        self.params = params

    @abstractmethod
    def execute(self) -> None:
        """Execute the refactoring and modify the file in place.

        Raises:
            ValueError: If refactoring cannot be applied
        """
        pass

    @abstractmethod
    def validate(self) -> None:
        """Validate parameters before execution.

        Raises:
            ValueError: If parameters are invalid
        """
        pass
