"""Add Parameter refactoring command."""

import ast

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    create_contact_info_body,
    find_method_in_tree,
    parse_target,
)


class AddParameterCommand(BaseCommand):
    """Command to add a parameter to a method."""

    name = "add-parameter"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply add-parameter refactoring using AST manipulation.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        name = self.params["name"]
        default = self.params.get("default")
        _, method_name = parse_target(target)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to add a parameter to the method.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If method not found or is not an instance method
            """
            result = find_method_in_tree(tree, method_name)
            if result is None:
                raise ValueError(f"Method '{method_name}' not found in {self.file_path}")

            class_node, method_node = result

            if not method_node.args.args or method_node.args.args[0].arg != "self":
                raise ValueError(f"Method '{method_name}' is not an instance method")

            new_arg = ast.arg(arg=name, annotation=None)
            method_node.args.args.insert(1, new_arg)

            if default:
                default_val = ast.parse(default, mode="eval").body
                method_node.args.defaults.append(default_val)

            # Update method body for specific known cases
            if name == "include_email" and method_name == "get_contact_info":
                method_node.body = create_contact_info_body(name)

            return tree

        self.apply_ast_transform(transform)


# Register the command
register_command(AddParameterCommand)
