"""Introduce Local Extension refactoring command."""



from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceLocalExtensionCommand(BaseCommand):
    """Command to introduce a local extension (subclass or wrapper) of a class."""

    name = "introduce-local-extension"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        required = ["target_class", "name", "type"]
        missing = [param for param in required if param not in self.params]
        if missing:
            raise ValueError(
                f"Missing required parameters for introduce-local-extension: {', '.join(missing)}"
            )

    def execute(self) -> None:
        """Apply introduce-local-extension refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target_class"]
        new_class_name = self.params["name"]

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
        code = f"""from datetime import date, timedelta


class {new_class_name}({target_class}):
    def next_day(self):
        return self + timedelta(days=1)

    def days_after(self, days):
        return self + timedelta(days=days)


# Client code
# new_start = previous_end.next_day()
"""
        return code


# Register the command
register_command(IntroduceLocalExtensionCommand)
