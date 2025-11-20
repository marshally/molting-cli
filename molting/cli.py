"""CLI entry point for molting."""

import click
from pathlib import Path
from typing import Type, List, Tuple

from molting import __version__
from molting.core.refactoring_base import RefactoringBase

# Import all refactoring classes
from molting.refactorings.composing_methods.rename import Rename
from molting.refactorings.composing_methods.inline_method import InlineMethod
from molting.refactorings.composing_methods.inline_temp import InlineTemp
from molting.refactorings.composing_methods.extract_method import ExtractMethod
from molting.refactorings.composing_methods.extract_variable import ExtractVariable
from molting.refactorings.composing_methods.introduce_explaining_variable import IntroduceExplainingVariable
from molting.refactorings.composing_methods.split_temporary_variable import SplitTemporaryVariable
from molting.refactorings.moving_features.move_method import MoveMethod
from molting.refactorings.moving_features.move_field import MoveField
from molting.refactorings.organizing_data.encapsulate_field import EncapsulateField
from molting.refactorings.organizing_data.replace_magic_number_with_symbolic_constant import ReplaceMagicNumberWithSymbolicConstant
from molting.refactorings.simplifying_method_calls.replace_constructor_with_factory_function import ReplaceConstructorWithFactoryFunction
from molting.refactorings.simplifying_method_calls.introduce_parameter import IntroduceParameter
from molting.refactorings.simplifying_conditionals.introduce_assertion import IntroduceAssertion
from molting.refactorings.composing_methods.remove_assignments_to_parameters import RemoveAssignmentsToParameters


# Registry mapping refactoring names to (class, param_names)
REFACTORING_REGISTRY: dict[str, Tuple[Type[RefactoringBase], List[str]]] = {
    "rename": (Rename, ["target", "new_name"]),
    "extract-method": (ExtractMethod, ["target", "name"]),
    "extract-variable": (ExtractVariable, ["target", "variable_name"]),
    "introduce-explaining-variable": (IntroduceExplainingVariable, ["target", "name"]),
    "inline": (InlineMethod, ["target"]),
    "inline-temp": (InlineTemp, ["target"]),
    "split-temporary-variable": (SplitTemporaryVariable, ["target"]),
    "move-method": (MoveMethod, ["source", "to"]),
    "move-field": (MoveField, ["source", "to"]),
    "encapsulate-field": (EncapsulateField, ["target"]),
    "replace-magic-number-with-symbolic-constant": (ReplaceMagicNumberWithSymbolicConstant, ["target", "magic_number", "constant_name"]),
    "replace-constructor-with-factory-function": (ReplaceConstructorWithFactoryFunction, ["target"]),
    "introduce-parameter": (IntroduceParameter, ["target", "name", "default"]),
    "introduce-assertion": (IntroduceAssertion, ["target", "condition", "message"]),
    "remove-assignments-to-parameters": (RemoveAssignmentsToParameters, ["target"]),
}


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
    if refactoring_name not in REFACTORING_REGISTRY:
        raise ValueError(f"Unknown refactoring: {refactoring_name}")

    refactor_class, param_names = REFACTORING_REGISTRY[refactoring_name]
    params = [kwargs.get(p) for p in param_names]
    refactor = refactor_class(file_path, *params)
    refactored_code = refactor.apply(refactor.source)
    Path(file_path).write_text(refactored_code)


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


@main.command(name="split-temporary-variable")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def split_temporary_variable(file_path: str, target: str) -> None:
    """Split a temporary variable assigned multiple times.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target variable to split (e.g., "function_name::var_name" or "ClassName::method_name::var_name")
    """
    refactor_file("split-temporary-variable", file_path, target=target)
    click.echo(f"✓ Split temporary variable '{target}' in {file_path}")


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


@main.command(name="introduce-explaining-variable")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("name")
def introduce_explaining_variable(file_path: str, target: str, name: str) -> None:
    """Extract a complex expression into a named variable for improved readability.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target location with line number (e.g., "function_name#L10")
        NAME: Name for the new explaining variable
    """
    refactor_file("introduce-explaining-variable", file_path, target=target, name=name)
    click.echo(f"✓ Introduced explaining variable '{name}' at '{target}' in {file_path}")


@main.command(name="replace-magic-number-with-symbolic-constant")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("magic_number")
@click.argument("constant_name")
def replace_magic_number_with_symbolic_constant(
    file_path: str, target: str, magic_number: str, constant_name: str
) -> None:
    """Replace a magic number with a named symbolic constant.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target location with line number (e.g., "function_name#L10")
        MAGIC_NUMBER: The numeric literal to replace (as a string)
        CONSTANT_NAME: Name of the constant to create
    """
    refactor_file(
        "replace-magic-number-with-symbolic-constant",
        file_path,
        target=target,
        magic_number=magic_number,
        constant_name=constant_name
    )
    click.echo(f"✓ Replaced magic number '{magic_number}' with constant '{constant_name}' in {file_path}")


@main.command(name="remove-assignments-to-parameters")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def remove_assignments_to_parameters(file_path: str, target: str) -> None:
    """Remove assignments to parameters by using a temporary variable instead.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function name (e.g., "function_name" or "ClassName::method_name")
    """
    refactor_file("remove-assignments-to-parameters", file_path, target=target)
    click.echo(f"✓ Removed assignments to parameters in '{target}' in {file_path}")
