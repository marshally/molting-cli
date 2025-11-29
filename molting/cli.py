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
