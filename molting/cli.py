"""CLI entry point for molting."""

from pathlib import Path
from typing import Any

import click

from molting import __version__
from molting.commands.registry import apply_refactoring, discover_and_register_commands

# Dynamically discover and import all command modules
discover_and_register_commands()


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Molting - Python refactoring CLI tool.

    Based on Martin Fowler's refactoring catalog, this tool provides
    automated refactorings for Python code.
    """
    pass


def refactor_file(refactoring_name: str, file_path: Path, **params: Any) -> None:
    """Apply a refactoring to a file.

    Args:
        refactoring_name: Name of the refactoring to apply
        file_path: Path to the file to refactor
        **params: Additional parameters for the refactoring

    Raises:
        ValueError: If refactoring_name is not recognized
    """
    apply_refactoring(refactoring_name, file_path, **params)


def refactor_directory(refactoring_name: str, directory: Path, **params: Any) -> None:
    """Apply a refactoring across all Python files in a directory.

    This is useful for refactorings that update call sites across multiple files,
    such as rename-method.

    Args:
        refactoring_name: Name of the refactoring to apply
        directory: Path to the directory containing Python files
        **params: Additional parameters for the refactoring

    Raises:
        ValueError: If refactoring_name is not recognized or directory doesn't exist
    """
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Find all Python files in the directory
    py_files = list(directory.glob("*.py"))
    if not py_files:
        raise ValueError(f"No Python files found in {directory}")

    # Apply refactoring to each file
    for file_path in py_files:
        apply_refactoring(refactoring_name, file_path, **params)
