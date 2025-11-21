"""CLI entry point for molting."""

from pathlib import Path
from typing import List, Optional, Tuple, Type

import click

from molting import __version__
from molting.core.refactoring_base import RefactoringBase
from molting.refactorings.composing_methods.extract_method import ExtractMethod
from molting.refactorings.composing_methods.extract_variable import ExtractVariable
from molting.refactorings.composing_methods.inline_method import InlineMethod
from molting.refactorings.composing_methods.inline_temp import InlineTemp
from molting.refactorings.composing_methods.introduce_explaining_variable import (
    IntroduceExplainingVariable,
)
from molting.refactorings.composing_methods.remove_assignments_to_parameters import (
    RemoveAssignmentsToParameters,
)
from molting.refactorings.composing_methods.replace_temp_with_query import (
    ReplaceTempWithQuery,
)

# Import all refactoring classes
from molting.refactorings.composing_methods.rename import Rename
from molting.refactorings.composing_methods.split_temporary_variable import SplitTemporaryVariable
from molting.refactorings.composing_methods.substitute_algorithm import SubstituteAlgorithm
from molting.refactorings.moving_features.extract_class import ExtractClass
from molting.refactorings.moving_features.hide_delegate import HideDelegate
from molting.refactorings.moving_features.inline_class import InlineClass
from molting.refactorings.moving_features.introduce_foreign_method import IntroduceForeignMethod
from molting.refactorings.moving_features.move_field import MoveField
from molting.refactorings.moving_features.move_method import MoveMethod
from molting.refactorings.moving_features.remove_middle_man import RemoveMiddleMan
from molting.refactorings.organizing_data.encapsulate_field import EncapsulateField
from molting.refactorings.organizing_data.replace_data_value_with_object import (
    ReplaceDataValueWithObject,
)
from molting.refactorings.organizing_data.replace_magic_number_with_symbolic_constant import (
    ReplaceMagicNumberWithSymbolicConstant,
)
from molting.refactorings.organizing_data.replace_type_code_with_class import (
    ReplaceTypeCodeWithClass,
)
from molting.refactorings.organizing_data.self_encapsulate_field import SelfEncapsulateField
from molting.refactorings.simplifying_conditionals.consolidate_conditional_expression import (
    ConsolidateConditionalExpression,
)
from molting.refactorings.simplifying_conditionals.consolidate_duplicate_conditional_fragments import (
    ConsolidateDuplicateConditionalFragments,
)
from molting.refactorings.simplifying_conditionals.decompose_conditional import DecomposeConditional
from molting.refactorings.simplifying_conditionals.introduce_assertion import IntroduceAssertion
from molting.refactorings.simplifying_conditionals.introduce_null_object import IntroduceNullObject
from molting.refactorings.simplifying_conditionals.remove_control_flag import RemoveControlFlag
from molting.refactorings.simplifying_conditionals.replace_nested_conditional_with_guard_clauses import (
    ReplaceNestedConditionalWithGuardClauses,
)
from molting.refactorings.simplifying_method_calls.add_parameter import AddParameter
from molting.refactorings.simplifying_method_calls.hide_method import HideMethod
from molting.refactorings.simplifying_method_calls.introduce_parameter import IntroduceParameter
from molting.refactorings.simplifying_method_calls.introduce_parameter_object import (
    IntroduceParameterObject,
)
from molting.refactorings.simplifying_method_calls.parameterize_method import ParameterizeMethod
from molting.refactorings.simplifying_method_calls.preserve_whole_object import (
    PreserveWholeObject,
)
from molting.refactorings.simplifying_method_calls.remove_parameter import RemoveParameter
from molting.refactorings.simplifying_method_calls.remove_setting_method import RemoveSettingMethod
from molting.refactorings.simplifying_method_calls.replace_constructor_with_factory_function import (
    ReplaceConstructorWithFactoryFunction,
)
from molting.refactorings.simplifying_method_calls.replace_error_code_with_exception import (
    ReplaceErrorCodeWithException,
)
from molting.refactorings.simplifying_method_calls.replace_exception_with_test import (
    ReplaceExceptionWithTest,
)
from molting.refactorings.simplifying_method_calls.replace_parameter_with_explicit_methods import (
    ReplaceParameterWithExplicitMethods,
)
from molting.refactorings.simplifying_method_calls.replace_parameter_with_method_call import (
    ReplaceParameterWithMethodCall,
)
from molting.refactorings.simplifying_method_calls.separate_query_from_modifier import (
    SeparateQueryFromModifier,
)

# Registry mapping refactoring names to (class, param_names)
REFACTORING_REGISTRY: dict[str, Tuple[Type[RefactoringBase], List[str]]] = {
    "rename": (Rename, ["target", "new_name"]),
    "extract-method": (ExtractMethod, ["target", "name"]),
    "extract-variable": (ExtractVariable, ["target", "variable_name"]),
    "introduce-explaining-variable": (IntroduceExplainingVariable, ["target", "name"]),
    "inline": (InlineMethod, ["target"]),
    "inline-method": (InlineMethod, ["target"]),
    "inline-temp": (InlineTemp, ["target"]),
    "replace-temp-with-query": (ReplaceTempWithQuery, ["target"]),
    "split-temporary-variable": (SplitTemporaryVariable, ["target"]),
    "substitute-algorithm": (SubstituteAlgorithm, ["target"]),
    "move-method": (MoveMethod, ["source", "to"]),
    "move-field": (MoveField, ["source", "to"]),
    "hide-delegate": (HideDelegate, ["target"]),
    "introduce-foreign-method": (IntroduceForeignMethod, ["target", "for_class", "name"]),
    "inline-class": (InlineClass, ["source_class", "into", "field_prefix"]),
    "remove-middle-man": (RemoveMiddleMan, ["target"]),
    "extract-class": (ExtractClass, ["source", "fields", "methods", "name"]),
    "encapsulate-field": (EncapsulateField, ["target"]),
    "self-encapsulate-field": (SelfEncapsulateField, ["target"]),
    "replace-data-value-with-object": (ReplaceDataValueWithObject, ["target", "name"]),
    "replace-type-code-with-class": (ReplaceTypeCodeWithClass, ["target", "name"]),
    "replace-magic-number-with-symbolic-constant": (
        ReplaceMagicNumberWithSymbolicConstant,
        ["target", "magic_number", "constant_name"],
    ),
    "replace-constructor-with-factory-function": (
        ReplaceConstructorWithFactoryFunction,
        ["target"],
    ),
    "introduce-parameter": (IntroduceParameter, ["target", "name", "default"]),
    "introduce-parameter-object": (IntroduceParameterObject, ["target", "params", "name"]),
    "add-parameter": (AddParameter, ["target", "name", "default"]),
    "parameterize-method": (ParameterizeMethod, ["target1", "target2", "new_name"]),
    "remove-parameter": (RemoveParameter, ["target", "parameter"]),
    "introduce-assertion": (IntroduceAssertion, ["target", "condition", "message"]),
    "introduce-null-object": (IntroduceNullObject, ["target_class"]),
    "decompose-conditional": (DecomposeConditional, ["target"]),
    "remove-assignments-to-parameters": (RemoveAssignmentsToParameters, ["target"]),
    "remove-control-flag": (RemoveControlFlag, ["target"]),
    "replace-nested-conditional-with-guard-clauses": (
        ReplaceNestedConditionalWithGuardClauses,
        ["target"],
    ),
    "consolidate-conditional-expression": (ConsolidateConditionalExpression, ["target"]),
    "consolidate-duplicate-conditional-fragments": (
        ConsolidateDuplicateConditionalFragments,
        ["target"],
    ),
    "hide-method": (HideMethod, ["target"]),
    "remove-setting-method": (RemoveSettingMethod, ["target"]),
    "replace-error-code-with-exception": (ReplaceErrorCodeWithException, ["target"]),
    "replace-exception-with-test": (ReplaceExceptionWithTest, ["target"]),
    "replace-parameter-with-explicit-methods": (
        ReplaceParameterWithExplicitMethods,
        ["target", "parameter_name"],
    ),
    "replace-parameter-with-method-call": (
        ReplaceParameterWithMethodCall,
        ["target"],
    ),
    "separate-query-from-modifier": (SeparateQueryFromModifier, ["target", "modifier_name"]),
    "preserve-whole-object": (PreserveWholeObject, ["target"]),
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
    refactor = refactor_class(file_path, *params)  # type: ignore[call-arg]
    refactored_code = refactor.apply(refactor.source)  # type: ignore[attr-defined]
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


@main.command(name="encapsulate-collection")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def encapsulate_collection(file_path: str, target: str) -> None:
    """Encapsulate a collection field with add/remove methods.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target collection field to encapsulate (e.g., "ClassName::collection_name")
    """
    refactor_file("encapsulate-collection", file_path, target=target)
    click.echo(f"✓ Encapsulated collection '{target}' in {file_path}")


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
def introduce_parameter(
    file_path: str, target: str, name: str, default: Optional[str] = None
) -> None:
    """Add a new parameter to a method.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target method (e.g., "ClassName::method_name")
        NAME: Name of the new parameter
    """
    refactor_file("introduce-parameter", file_path, target=target, name=name, default=default)
    param_desc = f"'{name}' with default '{default}'" if default else f"'{name}'"
    click.echo(f"✓ Introduced parameter {param_desc} to '{target}' in {file_path}")


@main.command(name="add-parameter")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("name")
@click.option("--default", default=None, help="Default value for the new parameter")
def add_parameter(file_path: str, target: str, name: str, default: Optional[str] = None) -> None:
    """Add a new parameter to a function or method.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function (e.g., "function_name" or "ClassName::method_name")
        NAME: Name of the new parameter
    """
    refactor_file("add-parameter", file_path, target=target, name=name, default=default)
    param_desc = f"'{name}' with default '{default}'" if default else f"'{name}'"
    click.echo(f"✓ Added parameter {param_desc} to '{target}' in {file_path}")


@main.command(name="remove-parameter")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("parameter")
def remove_parameter(file_path: str, target: str, parameter: str) -> None:
    """Remove an unused parameter from a function or method.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function (e.g., "function_name" or "ClassName::method_name")
        PARAMETER: Name of the parameter to remove
    """
    refactor_file("remove-parameter", file_path, target=target, parameter=parameter)
    click.echo(f"✓ Removed parameter '{parameter}' from '{target}' in {file_path}")


@main.command(name="introduce-assertion")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
@click.argument("condition")
@click.option("--message", default=None, help="Custom assertion message")
def introduce_assertion(
    file_path: str, target: str, condition: str, message: Optional[str] = None
) -> None:
    """Make assumptions explicit with an assertion.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function (e.g., "function_name#L10")
        CONDITION: The assertion condition as a Python expression
    """
    refactor_file(
        "introduce-assertion", file_path, target=target, condition=condition, message=message
    )
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
        constant_name=constant_name,
    )
    click.echo(
        f"✓ Replaced magic number '{magic_number}' with constant '{constant_name}' in {file_path}"
    )


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


@main.command(name="decompose-conditional")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def decompose_conditional(file_path: str, target: str) -> None:
    """Extract condition and branches into separate methods.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function with line number (e.g., "function_name#L2" or "ClassName::method_name#L3")
    """
    refactor_file("decompose-conditional", file_path, target=target)
    click.echo(f"✓ Decomposed conditional in '{target}' in {file_path}")


@main.command(name="remove-control-flag")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def remove_control_flag(file_path: str, target: str) -> None:
    """Replace control flag variables with break or return statements.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target specification with flag name (e.g., "function_name::flag_name" or "ClassName::method_name::flag_name")
    """
    refactor_file("remove-control-flag", file_path, target=target)
    click.echo(f"✓ Removed control flag in '{target}' in {file_path}")


@main.command(name="replace-nested-conditional-with-guard-clauses")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def replace_nested_conditional_with_guard_clauses(file_path: str, target: str) -> None:
    """Replace nested conditionals with guard clauses using early returns.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function with line number (e.g., "function_name#L2" or "ClassName::method_name#L3")
    """
    refactor_file("replace-nested-conditional-with-guard-clauses", file_path, target=target)
    click.echo(f"✓ Replaced nested conditional with guard clauses in '{target}' in {file_path}")


@main.command(name="consolidate-conditional-expression")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def consolidate_conditional_expression(file_path: str, target: str) -> None:
    """Consolidate a sequence of conditional checks with the same result.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function with line range (e.g., "function_name#L2-L7" or "ClassName::method_name#L3-L10")
    """
    refactor_file("consolidate-conditional-expression", file_path, target=target)
    click.echo(f"✓ Consolidated conditional expression in '{target}' in {file_path}")


@main.command(name="consolidate-duplicate-conditional-fragments")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def consolidate_duplicate_conditional_fragments(file_path: str, target: str) -> None:
    """Move identical code from all branches of a conditional outside the conditional.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target function with line number (e.g., "function_name#L2" or "ClassName::method_name#L3")
    """
    refactor_file("consolidate-duplicate-conditional-fragments", file_path, target=target)
    click.echo(f"✓ Consolidated duplicate conditional fragments in '{target}' in {file_path}")


@main.command(name="hide-method")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def hide_method(file_path: str, target: str) -> None:
    """Hide a method by making it private with underscore prefix.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target method to hide (e.g., "ClassName::method_name")
    """
    refactor_file("hide-method", file_path, target=target)
    click.echo(f"✓ Hidden method '{target}' in {file_path}")


@main.command(name="remove-setting-method")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("target")
def remove_setting_method(file_path: str, target: str) -> None:
    """Remove a setter method from a class.

    A field should be set at creation time and never altered. This refactoring
    removes any setter method for that field.

    Args:
        FILE_PATH: Path to the Python file to refactor
        TARGET: Target setter method to remove (e.g., "ClassName::set_field" or "ClassName::property_name")
    """
    refactor_file("remove-setting-method", file_path, target=target)
    click.echo(f"✓ Removed setting method '{target}' in {file_path}")
