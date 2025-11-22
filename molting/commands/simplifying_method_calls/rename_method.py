"""Rename Method refactoring command."""

from rope.base.project import Project  # type: ignore[import-untyped]
from rope.refactor.rename import Rename  # type: ignore[import-untyped]

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
        try:
            _ = self.params["target"]
            _ = self.params["new_name"]
        except KeyError as e:
            raise ValueError(f"Missing required parameter for rename-method: {e}") from e

    def execute(self) -> None:
        """Apply rename-method refactoring using rope library.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        new_name = self.params["new_name"]

        _, method_name = parse_target(target)

        project = Project(str(self.file_path.parent))
        try:
            resource = project.get_file(str(self.file_path.name))
            source = resource.read()

            offset = source.find(f"def {method_name}")
            if offset == -1:
                raise ValueError(f"Method '{method_name}' not found in {self.file_path}")

            rename_refactoring = Rename(project, resource, offset + len("def "))
            changes = rename_refactoring.get_changes(new_name)
            project.do(changes)
        finally:
            project.close()


# Register the command
register_command(RenameMethodCommand)
