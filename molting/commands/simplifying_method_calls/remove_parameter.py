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
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-parameter refactoring using AST manipulation.

        Raises:
            ValueError: If method or parameter not found
        """
        target = self.params["target"]
        _, method_name, param_name = parse_target(target, expected_parts=3)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to remove a parameter from the method.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If method or parameter not found
            """
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

            # Remove arguments from all call sites
            # Note: param_index in method calls excludes the implicit 'self' parameter
            call_arg_index = param_index - 1 if param_index > 0 else 0
            tree = RemoveArgumentTransformer(method_name, call_arg_index).visit(tree)

            return tree

        self.apply_ast_transform(transform)


class RemoveArgumentTransformer(ast.NodeTransformer):
    """Transformer to remove arguments from method calls."""

    def __init__(self, method_name: str, param_index: int) -> None:
        """Initialize the transformer.

        Args:
            method_name: Name of the method being modified
            param_index: Index of the parameter to remove
        """
        self.method_name = method_name
        self.param_index = param_index

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Visit a Call node and remove the argument at param_index if this is a call to method_name.

        Args:
            node: The Call node to visit

        Returns:
            The modified Call node
        """
        # First, recursively visit child nodes
        self.generic_visit(node)

        # Check if this is a call to the method we're modifying
        if isinstance(node.func, ast.Attribute) and node.func.attr == self.method_name:
            # Remove the argument at param_index if it exists
            if self.param_index < len(node.args):
                node.args.pop(self.param_index)

        return node


# Register the command
register_command(RemoveParameterCommand)
