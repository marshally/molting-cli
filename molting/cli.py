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
    from molting.refactorings.moving_features.move_field import MoveField
    from molting.refactorings.organizing_data.encapsulate_field import EncapsulateField
    from molting.refactorings.simplifying_method_calls.replace_constructor_with_factory_function import ReplaceConstructorWithFactoryFunction
    from molting.refactorings.simplifying_method_calls.introduce_parameter import IntroduceParameter
    from molting.refactorings.simplifying_conditionals.introduce_assertion import IntroduceAssertion

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
    elif refactoring_name == "move-field":
        source = kwargs.get("source")
        to = kwargs.get("to")
        refactor = MoveField(file_path, source, to)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "encapsulate-field":
        target = kwargs.get("target")
        refactor = EncapsulateField(file_path, target)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "replace-constructor-with-factory-function":
        target = kwargs.get("target")
        refactor = ReplaceConstructorWithFactoryFunction(file_path, target)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "introduce-parameter":
        target = kwargs.get("target")
        name = kwargs.get("name")
        default = kwargs.get("default")
        refactor = IntroduceParameter(file_path, target, name, default)
        refactored_code = refactor.apply(refactor.source)
        Path(file_path).write_text(refactored_code)
    elif refactoring_name == "introduce-assertion":
        target = kwargs.get("target")
        condition = kwargs.get("condition")
        message = kwargs.get("message")
        refactor = IntroduceAssertion(file_path, target, condition, message)
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


@main.command(name="encapsulate-field")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def encapsulate_field(file_path: str, target: str) -> None:
    """Make a field private with getter/setter property accessors.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target field to encapsulate (e.g., "ClassName::field_name")
    """
    refactor_file("encapsulate-field", file_path, target=target)
    click.echo(f"✓ Encapsulated field '{target}' in {file_path}")


@main.command(name="replace-constructor-with-factory-function")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def replace_constructor_with_factory_function(file_path: str, target: str) -> None:
    """Replace a constructor with a factory function.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target class name (e.g., "ClassName")
    """
    refactor_file("replace-constructor-with-factory-function", file_path, target=target)
    click.echo(f"✓ Replaced constructor with factory function for '{target}' in {file_path}")


@main.command(name="introduce-parameter")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("name")
@click.option("--default", default=None, help="Default value for the new parameter")
def introduce_parameter(file_path: str, target: str, name: str, default: str = None) -> None:
    """Add a new parameter to a method.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target method (e.g., "ClassName::method_name")
        NAME: Name of the new parameter
    """
    refactor_file("introduce-parameter", file_path, target=target, name=name, default=default)
    param_desc = f"'{name}' with default '{default}'" if default else f"'{name}'"
    click.echo(f"✓ Introduced parameter {param_desc} to '{target}' in {file_path}")


@main.command(name="introduce-assertion")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("condition")
@click.option("--message", default=None, help="Custom assertion message")
def introduce_assertion(file_path: str, target: str, condition: str, message: str = None) -> None:
    """Make assumptions explicit with an assertion.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function (e.g., "function_name#L10")
        CONDITION: The assertion condition as a Python expression
    """
    refactor_file("introduce-assertion", file_path, target=target, condition=condition, message=message)
    click.echo(f"✓ Introduced assertion '{condition}' to '{target}' in {file_path}")
