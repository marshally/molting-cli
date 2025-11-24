"""Remove Setting Method refactoring command."""

import ast

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class RemoveSettingMethodCommand(BaseCommand):
    """Command to remove a setter method to make a field immutable."""

    name = "remove-setting-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-setting-method refactoring using AST manipulation.

        Raises:
            ValueError: If class or field not found
        """
        target = self.params["target"]
        class_name, field_name = parse_target(target, expected_parts=2)

        # Determine setter method name from field name
        # Field _id -> setter set_id
        # Remove leading underscore if present
        clean_field_name = field_name.lstrip("_")
        setter_name = f"set_{clean_field_name}"

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to remove the setter method.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If class or setter method not found
            """
            # Find the class
            class_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    class_node = node
                    break

            if class_node is None:
                raise ValueError(f"Class '{class_name}' not found in {self.file_path}")

            # Find and remove the setter method
            method_index = None
            for i, item in enumerate(class_node.body):
                if isinstance(item, ast.FunctionDef) and item.name == setter_name:
                    method_index = i
                    break

            if method_index is None:
                raise ValueError(f"Setter method '{setter_name}' not found in class '{class_name}'")

            # Remove the setter method
            class_node.body.pop(method_index)

            return tree

        self.apply_ast_transform(transform)


# Register the command
register_command(RemoveSettingMethodCommand)
