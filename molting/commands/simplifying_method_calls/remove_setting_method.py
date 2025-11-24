"""Remove Setting Method refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class RemoveSettingMethodCommand(BaseCommand):
    """Command to remove a setter method to make a field immutable."""

    name = "remove-setting-method"

    def _derive_setter_name(self, field_name: str) -> str:
        """Derive the setter method name from a field name.

        Args:
            field_name: The field name (e.g., '_id', 'name')

        Returns:
            The setter method name (e.g., 'set_id', 'set_name')
        """
        clean_field_name = field_name.lstrip("_")
        return f"set_{clean_field_name}"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-setting-method refactoring using libCST.

        Raises:
            ValueError: If class or field not found
        """
        target = self.params["target"]
        class_name, field_name = parse_target(target, expected_parts=2)
        setter_name = self._derive_setter_name(field_name)

        # Apply the transformation
        self.apply_libcst_transform(RemoveSettingMethodTransformer, class_name, setter_name)


class RemoveSettingMethodTransformer(cst.CSTTransformer):
    """Transforms a class to remove a setter method."""

    def __init__(self, class_name: str, setter_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the setter method
            setter_name: Name of the setter method to remove
        """
        self.class_name = class_name
        self.setter_name = setter_name
        self.in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and remove the setter method if found."""
        if original_node.name.value == self.class_name:
            self.in_target_class = False

            # Filter out the setter method from the class body
            if isinstance(updated_node.body, cst.IndentedBlock):
                new_body = []
                setter_found = False

                for stmt in updated_node.body.body:
                    if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.setter_name:
                        setter_found = True
                        continue  # Skip this method
                    new_body.append(stmt)

                if not setter_found:
                    raise ValueError(
                        f"Setter method '{self.setter_name}' not found in class '{self.class_name}'"
                    )

                # Return the class with updated body
                return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

        return updated_node


# Register the command
register_command(RemoveSettingMethodCommand)
