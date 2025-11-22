"""CLI entry point for molting."""

from pathlib import Path

import click
from rope.base.project import Project
from rope.refactor.rename import Rename

from molting import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Molting - Python refactoring CLI tool.

    Based on Martin Fowler's refactoring catalog, this tool provides
    automated refactorings for Python code.
    """
    pass


def refactor_file(refactoring_name: str, file_path: Path, **params) -> None:
    """Apply a refactoring to a file.

    Args:
        refactoring_name: Name of the refactoring to apply
        file_path: Path to the file to refactor
        **params: Additional parameters for the refactoring
    """
    if refactoring_name == "rename-method":
        try:
            target = params["target"]
            new_name = params["new_name"]
        except KeyError as e:
            raise ValueError(f"Missing required parameter for rename-method: {e}") from e

        # Parse target: "ClassName::method_name"
        parts = target.split("::")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid target format '{target}'. Expected 'ClassName::method_name'"
            )
        _, method_name = parts

        # Open rope project
        project = Project(str(file_path.parent))
        try:
            resource = project.get_file(str(file_path.name))
            source = resource.read()

            # Find the method definition
            # Simple approach: find "def method_name"
            offset = source.find(f"def {method_name}")
            if offset == -1:
                raise ValueError(f"Method '{method_name}' not found in {file_path}")

            # Create rename refactoring
            rename = Rename(project, resource, offset + len("def "))
            changes = rename.get_changes(new_name)
            project.do(changes)
        finally:
            project.close()


# Refactoring commands will be added here
