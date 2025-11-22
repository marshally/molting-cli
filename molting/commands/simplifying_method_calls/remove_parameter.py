"""Remove Parameter refactoring command."""

import ast

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    find_method_in_tree,
    parameter_has_default,
    parse_target,
)


class RemoveParameterCommand(BaseCommand):
    """Command to remove a parameter from a method."""

    name = "remove-parameter"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        try:
            _ = self.params["target"]
        except KeyError as e:
            raise ValueError(f"Missing required parameter for remove-parameter: {e}") from e

    def execute(self) -> None:
        """Apply remove-parameter refactoring using AST manipulation.

        Raises:
            ValueError: If method or parameter not found
        """
        target = self.params["target"]

        _, method_name, param_name = parse_target(target, expected_parts=3)

        source = self.file_path.read_text()
        tree = ast.parse(source)

        result = find_method_in_tree(tree, method_name)
        if result is None:
            raise ValueError(f"Method '{method_name}' not found in {self.file_path}")

        _, method_node = result

        # Find and remove the parameter from the method's argument list
        param_index = None
        for i, arg in enumerate(method_node.args.args):
            if arg.arg == param_name:
                param_index = i
                break

        if param_index is None:
            raise ValueError(f"Parameter '{param_name}' not found in method '{method_name}'")

        # Check if the parameter has a default value before removing
        total_args = len(method_node.args.args)
        num_defaults = len(method_node.args.defaults)
        has_default = parameter_has_default(param_index, total_args, num_defaults)

        # Remove the parameter from the argument list
        method_node.args.args.pop(param_index)

        # If the parameter had a default value, remove it from the defaults list
        if has_default:
            num_args_without_defaults = total_args - num_defaults
            default_index = param_index - num_args_without_defaults
            method_node.args.defaults.pop(default_index)

        ast.fix_missing_locations(tree)

        modified_source = ast.unparse(tree)
        self.file_path.write_text(modified_source)


# Register the command
register_command(RemoveParameterCommand)
