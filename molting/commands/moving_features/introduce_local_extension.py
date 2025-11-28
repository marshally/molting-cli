"""Introduce Local Extension refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.visitors import ClassConflictChecker


class IntroduceLocalExtensionCommand(BaseCommand):
    """Command to introduce a local extension (subclass or wrapper) of a class."""

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
        imports = self._generate_imports()
        class_definition = self._generate_class_definition(target_class, new_class_name)
        client_code = self._generate_client_code_template()

        return f"{imports}{class_definition}{client_code}"

    def _generate_imports(self) -> str:
        """Generate import statements.

        Returns:
            Import statements as a string
        """
        return "from datetime import date, timedelta\n\n\n"

    def _generate_class_definition(self, target_class: str, new_class_name: str) -> str:
        """Generate the extension class definition.

        Args:
            target_class: Name of the class to extend
            new_class_name: Name of the new extension class

        Returns:
            Class definition as a string
        """
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

    def _generate_client_code_template(self) -> str:
        """Generate client code comment template.

        Returns:
            Client code comments as a string
        """
        return "# Client code\n# new_start = previous_end.next_day()\n"


# Register the command
register_command(IntroduceLocalExtensionCommand)
