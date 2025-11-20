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
    from molting.refactorings.composing_methods.inline_method import InlineMethod
    from molting.refactorings.composing_methods.inline_temp import InlineTemp
    from molting.refactorings.composing_methods.extract_method import ExtractMethod
    from molting.refactorings.composing_methods.extract_variable import ExtractVariable
    from molting.refactorings.moving_features.move_method import MoveMethod
    from molting.refactorings.organizing_data.encapsulate_field import EncapsulateField

    if refactoring_name == "rename":
        target = kwargs.get("target")
        new_name = kwargs.get("new_name")
        refactor = Rename(file_path, target, new_name)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "extract-method":
        target = kwargs.get("target")
        name = kwargs.get("name")
        refactor = ExtractMethod(file_path, target, name)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "inline":
        target = kwargs.get("target")
        refactor = InlineMethod(file_path, target)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "inline-temp":
        target = kwargs.get("target")
        refactor = InlineTemp(file_path, target)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "extract-variable":
        target = kwargs.get("target")
        variable_name = kwargs.get("variable_name")
        refactor = ExtractVariable(file_path, target, variable_name)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "move-method":
        source = kwargs.get("source")
        to = kwargs.get("to")
        refactor = MoveMethod(file_path, source, to)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "encapsulate-field":
        target = kwargs.get("target")
        refactor = EncapsulateField(file_path, target)
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


@main.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def inline(file_path: str, target: str) -> None:
    """Inline a method by replacing its calls with the method's body.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target method to inline (e.g., "ClassName::method_name")
    """
    refactor_file("inline", file_path, target=target)
    click.echo(f"✓ Inlined '{target}' in {file_path}")
