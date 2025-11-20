"""CLI entry point for molting."""

import click

from molting import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Molting - Python refactoring CLI tool.

    Based on Martin Fowler's refactoring catalog, this tool provides
    automated refactorings for Python code.
    """
    pass


# Refactoring commands will be added here
