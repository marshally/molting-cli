"""Command registry for dynamic dispatch of refactorings."""

from pathlib import Path
from typing import Any, Dict, Type

from molting.commands.base import BaseCommand

_registry: Dict[str, Type[BaseCommand]] = {}


def register_command(command_class: Type[BaseCommand]) -> None:
    """Register a command class.

    Args:
        command_class: The command class to register

    Raises:
        ValueError: If command_class doesn't have a name attribute
    """
    if not hasattr(command_class, "name"):
        raise ValueError(f"Command class {command_class.__name__} must have a 'name' attribute")
    _registry[command_class.name] = command_class


def get_command(name: str) -> Type[BaseCommand]:
    """Get a command class by name.

    Args:
        name: The name of the command

    Returns:
        The command class

    Raises:
        ValueError: If command is not registered
    """
    if name not in _registry:
        raise ValueError(f"Unknown refactoring: {name}")
    return _registry[name]


def apply_refactoring(refactoring: str, file_path: Path, **params: Any) -> None:
    """Apply a refactoring using the registry.

    Args:
        refactoring: Name of the refactoring to apply
        file_path: Path to the file to refactor
        **params: Additional parameters for the refactoring

    Raises:
        ValueError: If refactoring is unknown or parameters are invalid
    """
    command_class = get_command(refactoring)
    command = command_class(file_path, **params)
    command.validate()
    command.execute()
