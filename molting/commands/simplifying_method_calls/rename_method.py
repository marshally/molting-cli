"""Rename Method refactoring command."""

import re

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class RenameMethodCommand(BaseCommand):
    """Rename a method to better reflect its purpose and improve code clarity.

    The Rename Method refactoring updates a method's name throughout the codebase
    to make the code more self-documenting and easier to understand. This is one of
    the most straightforward refactorings that significantly improves code readability.

    **When to use:**
    - A method name no longer accurately describes what the method does
    - The original name is confusing or misleading to other developers
    - You want to improve code clarity and maintainability
    - Method names should reveal intent and reduce the need for comments

    **Example:**
    Before:
        def calculate(self, items):
            return sum(item.price for item in items)

        total = order.calculate(products)

    After:
        def calculate_total_price(self, items):
            return sum(item.price for item in items)

        total = order.calculate_total_price(products)
    """

    name = "rename-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "new_name")

    def execute(self) -> None:
        """Apply rename-method refactoring.

        Renames the method definition (if present in this file) and all call sites.
        This supports both single-file and multi-file refactoring scenarios.

        Raises:
            ValueError: If target format is invalid
        """
        target = self.params["target"]
        new_name = self.params["new_name"]

        _, method_name = parse_target(target)

        # Read the source file
        source = self.file_path.read_text()
        result = source

        # Use regex to replace all method calls and definitions
        # This handles:
        # 1. Method definitions: def method_name(
        # 2. Method calls with self: self.method_name(
        # 3. Method calls with variables: var.method_name(
        # 4. Method calls with attributes: obj.attr.method_name(

        # Replace method definition (if it exists in this file)
        pattern = rf"\bdef {re.escape(method_name)}\("
        result = re.sub(pattern, f"def {new_name}(", result)

        # Replace all method calls with dot notation
        pattern = rf"\.{re.escape(method_name)}\("
        result = re.sub(pattern, f".{new_name}(", result)

        # Only write if changes were made
        if result != source:
            self.file_path.write_text(result)


# Register the command
register_command(RenameMethodCommand)
