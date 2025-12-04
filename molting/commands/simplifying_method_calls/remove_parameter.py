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
    """Remove an unused parameter from a method.

    The Remove Parameter refactoring eliminates a parameter that is no longer
    used by the method body. This simplifies the method's interface and reduces
    coupling between the method and its callers.

    **When to use:**
    - A parameter is no longer referenced in the method body
    - You want to simplify a method's interface
    - You're refactoring to reduce unnecessary dependencies
    - A parameter was previously used but is now redundant

    **Example:**
    Before:
        def calculate_total(items: list, tax_rate: float, discount: float) -> float:
            # tax_rate is no longer used
            return sum(item.price for item in items) - discount

        result = obj.calculate_total([item1, item2], 0.08, 5.0)

    After:
        def calculate_total(items: list, discount: float) -> float:
            return sum(item.price for item in items) - discount

        result = obj.calculate_total([item1, item2], 5.0)
    """

    name = "remove-parameter"

    # Class variable to cache parameter index for multi-file refactoring
    # Key: (method_name, param_name), Value: call_arg_index
    _param_index_cache: dict[tuple[str, str], int] = {}

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-parameter refactoring using AST manipulation.

        Supports both single-file and multi-file refactoring scenarios:
        - If the method definition is found in this file, removes the parameter from it
        - Always updates call sites in this file (if any exist)
        - Uses a class-level cache to share parameter index info across files

        Raises:
            ValueError: If method or parameter not found in the file containing the definition
        """
        target = self.params["target"]
        _, method_name, param_name = parse_target(target, expected_parts=3)
        cache_key = (method_name, param_name)

        # For multi-file refactoring, pre-scan the directory to find the method definition
        # This ensures we know the parameter index before processing all files
        if cache_key not in RemoveParameterCommand._param_index_cache:
            self._scan_for_parameter_index(method_name, param_name, cache_key)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to remove a parameter from the method.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If method is found but parameter is not
            """
            result = find_method_in_tree(tree, method_name)

            # Determine the parameter index for call site updates
            call_arg_index = None

            if result is not None:
                # Method definition found - remove parameter from signature
                _, method_node = result

                # Find and remove the parameter from the method's argument list
                param_index = None
                for i, arg in enumerate(method_node.args.args):
                    if arg.arg == param_name:
                        param_index = i
                        break

                if param_index is None:
                    raise ValueError(
                        f"Parameter '{param_name}' not found in method '{method_name}'"
                    )

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

                # Calculate call argument index (excludes implicit 'self' parameter)
                call_arg_index = param_index - 1 if param_index > 0 else 0

                # Cache the parameter index for other files
                RemoveParameterCommand._param_index_cache[cache_key] = call_arg_index
            else:
                # Method definition not in this file - check cache for parameter index
                call_arg_index = RemoveParameterCommand._param_index_cache.get(cache_key)

            # Remove arguments from all call sites (if any exist)
            if call_arg_index is not None:
                tree = RemoveArgumentTransformer(method_name, call_arg_index).visit(tree)

            return tree

        self.apply_ast_transform(transform)

    def _scan_for_parameter_index(
        self, method_name: str, param_name: str, cache_key: tuple[str, str]
    ) -> None:
        """Scan the directory for the method definition to determine parameter index.

        This is used for multi-file refactoring to ensure we know the parameter index
        before processing files that only contain call sites.

        Args:
            method_name: Name of the method to find
            param_name: Name of the parameter to remove
            cache_key: Cache key for storing the parameter index
        """
        # Check if the current file is in a directory (multi-file scenario)
        directory = self.file_path.parent
        if not directory.exists():
            return

        # Scan all Python files in the directory
        for py_file in directory.glob("*.py"):
            if py_file == self.file_path:
                # Skip current file as it will be processed normally
                continue

            try:
                source = py_file.read_text()
                tree = ast.parse(source)
                result = find_method_in_tree(tree, method_name)

                if result is not None:
                    _, method_node = result

                    # Find the parameter index
                    param_index = None
                    for i, arg in enumerate(method_node.args.args):
                        if arg.arg == param_name:
                            param_index = i
                            break

                    if param_index is not None:
                        # Calculate call argument index (excludes implicit 'self' parameter)
                        call_arg_index = param_index - 1 if param_index > 0 else 0
                        RemoveParameterCommand._param_index_cache[cache_key] = call_arg_index
                        return
            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue


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

    def visit_Call(self, node: ast.Call) -> ast.Call:  # noqa: N802
        """Visit a Call node and remove argument at param_index.

        This removes the argument at param_index if the call is to the
        method_name being modified.

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
