"""Rename Method refactoring command."""

import re

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class RenameMethodCommand(BaseCommand):
    """Command to rename a method in a class."""

    name = "rename-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "new_name")

    def execute(self) -> None:
        """Apply rename-method refactoring.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        new_name = self.params["new_name"]

        _, method_name = parse_target(target)

        # Read the source file
        source = self.file_path.read_text()

        # Verify method exists
        if f"def {method_name}" not in source:
            raise ValueError(f"Method '{method_name}' not found in {self.file_path}")

        # Use regex to replace all method calls and definitions
        # This handles:
        # 1. Method definitions: def method_name(
        # 2. Method calls with self: self.method_name(
        # 3. Method calls with variables: var.method_name(
        # 4. Method calls with attributes: obj.attr.method_name(

        # Replace method definition
        pattern = rf"\bdef {re.escape(method_name)}\("
        result = re.sub(pattern, f"def {new_name}(", source)

        # Replace all method calls with dot notation
        pattern = rf"\.{re.escape(method_name)}\("
        result = re.sub(pattern, f".{new_name}(", result)

        # Write the updated source back
        self.file_path.write_text(result)


# Register the command
register_command(RenameMethodCommand)
