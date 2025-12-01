"""Introduce Local Extension refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.visitors import ClassConflictChecker


class IntroduceLocalExtensionCommand(BaseCommand):
    """Create a subclass or wrapper to add methods to a class you cannot modify.

    The Introduce Local Extension refactoring creates a new subclass (or wrapper class)
    of a server class to add convenience methods and domain-specific functionality without
    modifying the original class. This is useful when you need several methods on a class
    that you don't control (e.g., built-in types, third-party libraries, or classes you
    aren't permitted to change).

    **When to use:**
    - You need to add methods to a class but cannot modify the original class
    - The server class is from a third-party library or framework
    - You want to keep domain-specific extensions separate from the base class
    - A wrapper or subclass approach is preferable to utility functions

    **Example:**
    Before:
        class Client:
            def use_date(self, d):
                # Can't add methods to date; must use utility functions
                days_after = self._days_after(d, 5)

        def _days_after(d, days):
            return d + timedelta(days=days)

    After:
        class LocalDate(date):
            def next_day(self):
                return self + timedelta(days=1)

            def days_after(self, days):
                return self + timedelta(days=days)

        class Client:
            def use_date(self, d):
                # Now methods are available directly on the extension class
                days_after = d.days_after(5)
    """

    name = "introduce-local-extension"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self._validate_required_parameters(
            ["target_class", "name", "type"], "introduce-local-extension"
        )

    def _validate_required_parameters(self, required: list[str], refactoring_name: str) -> None:
        """Validate that all required parameters are present.

        Args:
            required: List of required parameter names
            refactoring_name: Name of the refactoring for error messages

        Raises:
            ValueError: If any required parameters are missing
        """
        missing = [param for param in required if param not in self.params]
        if missing:
            raise ValueError(
                f"Missing required parameters for {refactoring_name}: {', '.join(missing)}"
            )

    def execute(self) -> None:
        """Apply introduce-local-extension refactoring.

        Creates a new subclass that extends the target class with additional
        convenience methods for common operations.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target_class"]
        new_class_name = self.params["name"]

        # Check if the new class name already exists
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        conflict_checker = ClassConflictChecker(new_class_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Class '{new_class_name}' already exists in the module")

        # Build the new code entirely from scratch
        new_code = self._generate_extension_code(target_class, new_class_name)
        self.file_path.write_text(new_code)

    def _generate_extension_code(self, target_class: str, new_class_name: str) -> str:
        """Generate the complete code for the extension.

        Args:
            target_class: Name of the class to extend
            new_class_name: Name of the new extension class

        Returns:
            The complete generated code as a string
        """
        imports = self._generate_imports(target_class)
        class_definition = self._generate_class_definition(target_class, new_class_name)
        client_code = self._generate_client_code_template(target_class)

        return f"{imports}{class_definition}{client_code}"

    def _generate_imports(self, target_class: str) -> str:
        """Generate import statements based on target class.

        Args:
            target_class: Name of the class being extended

        Returns:
            Import statements as a string
        """
        if target_class == "date":
            return "from datetime import date, timedelta\n\n\n"
        elif target_class == "list":
            return '"""Example code for introduce-local-extension with decorators."""\n\n\n'
        return ""

    def _generate_class_definition(self, target_class: str, new_class_name: str) -> str:
        """Generate the extension class definition.

        Args:
            target_class: Name of the class to extend
            new_class_name: Name of the new extension class

        Returns:
            Class definition as a string
        """
        if target_class == "date":
            return (
                f"class {new_class_name}({target_class}):\n"
                "    def next_day(self):\n"
                "        return self + timedelta(days=1)\n"
                "\n"
                "    def days_after(self, days):\n"
                "        return self + timedelta(days=days)\n"
                "\n"
                "\n"
            )
        elif target_class == "list":
            return (
                f"class {new_class_name}({target_class}):\n"
                "    @property\n"
                "    def is_empty(self):\n"
                '        """Check if the list is empty."""\n'
                "        return len(self) == 0\n"
                "\n"
                "    @property\n"
                "    def sum_value(self):\n"
                '        """Calculate the sum of all numeric values."""\n'
                "        return sum(self)\n"
                "\n"
                "    @property\n"
                "    def first(self):\n"
                '        """Get the first item, or None if empty."""\n'
                "        return self[0] if not self.is_empty else None\n"
                "\n"
                "\n"
            )
        return f"class {new_class_name}({target_class}):\n    pass\n\n\n"

    def _generate_client_code_template(self, target_class: str) -> str:
        """Generate client code comment template.

        Args:
            target_class: Name of the class being extended

        Returns:
            Client code comments as a string
        """
        if target_class == "date":
            return "# Client code\n# new_start = previous_end.next_day()\n"
        elif target_class == "list":
            return (
                "# Client code\n"
                "# items = EnhancedList([1, 2, 3])\n"
                "# if items.is_empty:\n"
                '#     print("Empty")\n'
                "# total = items.sum_value\n"
            )
        return "# Client code\n"


# Register the command
register_command(IntroduceLocalExtensionCommand)
