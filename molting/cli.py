"""CLI entry point for molting."""

from pathlib import Path
from typing import Any

import click

# Import commands to register them
import molting.commands.composing_methods.extract_function  # noqa: F401
import molting.commands.composing_methods.extract_method  # noqa: F401
import molting.commands.composing_methods.inline_method  # noqa: F401
import molting.commands.composing_methods.remove_assignments_to_parameters  # noqa: F401
import molting.commands.composing_methods.replace_method_with_method_object  # noqa: F401
import molting.commands.composing_methods.substitute_algorithm  # noqa: F401
import molting.commands.dealing_with_generalization.collapse_hierarchy  # noqa: F401
import molting.commands.dealing_with_generalization.extract_interface  # noqa: F401
import molting.commands.dealing_with_generalization.extract_subclass  # noqa: F401
import molting.commands.dealing_with_generalization.extract_superclass  # noqa: F401
import molting.commands.dealing_with_generalization.form_template_method  # noqa: F401
import molting.commands.dealing_with_generalization.push_down_field  # noqa: F401
import molting.commands.dealing_with_generalization.replace_delegation_with_inheritance  # noqa: F401
import molting.commands.dealing_with_generalization.replace_inheritance_with_delegation  # noqa: F401
import molting.commands.moving_features.extract_class  # noqa: F401
import molting.commands.moving_features.hide_delegate  # noqa: F401
import molting.commands.moving_features.inline_class  # noqa: F401
import molting.commands.moving_features.introduce_foreign_method  # noqa: F401
import molting.commands.moving_features.introduce_local_extension  # noqa: F401
import molting.commands.moving_features.move_field  # noqa: F401
import molting.commands.moving_features.move_method  # noqa: F401
import molting.commands.moving_features.remove_middle_man  # noqa: F401
import molting.commands.organizing_data.encapsulate_collection  # noqa: F401
import molting.commands.organizing_data.encapsulate_field  # noqa: F401
import molting.commands.organizing_data.replace_data_value_with_object  # noqa: F401
import molting.commands.organizing_data.replace_magic_number_with_symbolic_constant  # noqa: F401
import molting.commands.organizing_data.self_encapsulate_field  # noqa: F401
import molting.commands.simplifying_conditionals.consolidate_conditional_expression  # noqa: F401
import molting.commands.simplifying_conditionals.consolidate_duplicate_conditional_fragments  # noqa: F401
import molting.commands.simplifying_conditionals.decompose_conditional  # noqa: F401
import molting.commands.simplifying_conditionals.introduce_assertion  # noqa: F401
import molting.commands.simplifying_conditionals.remove_control_flag  # noqa: F401
import molting.commands.simplifying_conditionals.replace_nested_conditional_with_guard_clauses  # noqa: F401
import molting.commands.simplifying_method_calls.add_parameter  # noqa: F401
import molting.commands.simplifying_method_calls.hide_method  # noqa: F401
import molting.commands.simplifying_method_calls.parameterize_method  # noqa: F401
import molting.commands.simplifying_method_calls.remove_parameter  # noqa: F401
import molting.commands.simplifying_method_calls.remove_setting_method  # noqa: F401
import molting.commands.simplifying_method_calls.rename_method  # noqa: F401
import molting.commands.simplifying_method_calls.replace_constructor_with_factory_function  # noqa: F401
import molting.commands.simplifying_method_calls.replace_error_code_with_exception  # noqa: F401
from molting import __version__
from molting.commands.registry import apply_refactoring


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
