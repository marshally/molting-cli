"""Remove Setting Method refactoring command."""

import ast

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

    def _find_class_in_tree(self, tree: ast.Module, class_name: str) -> ast.ClassDef:
        """Find a class definition in the AST.

        Args:
            tree: The AST module to search
            class_name: The name of the class to find

        Returns:
            The class definition node

        Raises:
            ValueError: If class is not found
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
        raise ValueError(f"Class '{class_name}' not found in {self.file_path}")

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
        setter_name = self._derive_setter_name(field_name)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to remove the setter method.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If class or setter method not found
            """
            class_node = self._find_class_in_tree(tree, class_name)

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
