"""Base class for all refactoring commands."""

import ast
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

import libcst as cst


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

    def validate_required_params(self, *param_names: str) -> None:
        """Validate that required parameters are present.

        Args:
            *param_names: Names of required parameters

        Raises:
            ValueError: If any required parameters are missing
        """
        missing = [p for p in param_names if p not in self.params]
        if missing:
            raise ValueError(f"Missing required parameters for {self.name}: {', '.join(missing)}")

    @abstractmethod
    def validate(self) -> None:
        """Validate parameters before execution.

        Raises:
            ValueError: If parameters are invalid
        """
        pass

    def apply_libcst_transform(
        self, transformer_class: type[cst.CSTTransformer], *args: Any, **kwargs: Any
    ) -> None:
        """Apply a libCST transformer to the file.

        Args:
            transformer_class: The transformer class to instantiate
            *args: Positional arguments for transformer
            **kwargs: Keyword arguments for transformer
        """
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = transformer_class(*args, **kwargs)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)

    def apply_ast_transform(self, transform_func: Callable[[ast.Module], ast.Module]) -> None:
        """Apply an AST transformation function to the file.

        Args:
            transform_func: Function that takes and returns an ast.Module
        """
        source_code = self.file_path.read_text()
        tree = ast.parse(source_code)
        modified_tree = transform_func(tree)
        ast.fix_missing_locations(modified_tree)
        modified_source = ast.unparse(modified_tree)
        self.file_path.write_text(modified_source)
