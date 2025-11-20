"""CLI entry point for molting."""

import click
from pathlib import Path

from molting import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Molting - Python refactoring CLI tool.

    Based on Martin Fowler's refactoring catalog, this tool provides
    automated refactorings for Python code.
    """
    pass


def refactor_file(refactoring_name: str, file_path: str, **kwargs) -> None:
    """Apply a refactoring to a file.

    Args:
        refactoring_name: Name of the refactoring (e.g., "rename")
        file_path: Path to the file to refactor
        **kwargs: Additional parameters for the refactoring
    """
    from molting.refactorings.composing_methods.rename import Rename

    if refactoring_name == "rename":
        target = kwargs.get("target")
        new_name = kwargs.get("new_name")
        refactor = Rename(file_path, target, new_name)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    else:
        raise ValueError(f"Unknown refactoring: {refactoring_name}")


@main.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("new_name")
def rename(file_path: str, target: str, new_name: str) -> None:
    """Rename a variable, method, class, or module.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target identifier to rename (e.g., "function_name" or "ClassName::method_name")
        NEW_NAME: New name for the target
    """
    refactor_file("rename", file_path, target=target, new_name=new_name)
    click.echo(f"✓ Renamed '{target}' to '{new_name}' in {file_path}")
