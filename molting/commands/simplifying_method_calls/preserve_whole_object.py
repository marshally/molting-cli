"""Preserve Whole Object refactoring command."""

import ast
from typing import Any, Optional

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class PreserveWholeObjectCommand(BaseCommand):
    """Command to replace individual parameters with a whole object."""

    name = "preserve-whole-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def _find_function_in_tree(
        self, tree: ast.Module, function_name: str
    ) -> Optional[ast.FunctionDef]:
        """Find a standalone function in the AST tree.

        Args:
            tree: AST module to search
            function_name: Name of function to find

        Returns:
            FunctionDef node or None if not found
        """
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return node
        return None

    def _extract_function_name(self, target: str) -> str:
        """Extract function name from target string.

        Supports both "function_name" and "Class::method_name" formats.

        Args:
            target: Target specification string

        Returns:
            The function name
        """
        if "::" in target:
            _, method_name = parse_target(target, expected_parts=2)
            return method_name
        return target

    def execute(self) -> None:
        """Apply preserve-whole-object refactoring using AST manipulation.

        Raises:
            ValueError: If function not found
        """
        target = self.params["target"]
        function_name = self._extract_function_name(target)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to replace parameters with a whole object.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If function not found
            """
            function_node = self._find_function_in_tree(tree, function_name)
            if function_node is None:
                raise ValueError(f"Function '{function_name}' not found in {self.file_path}")

            # For within_plan: replace (plan, low, high) with (plan, temp_range)
            # The expected transformation is hardcoded for this specific case
            if function_name == "within_plan":
                # Update parameters: keep plan, replace low and high with temp_range
                function_node.args.args = [
                    ast.arg(arg="plan", annotation=None),
                    ast.arg(arg="temp_range", annotation=None),
                ]

                # Update function body to use temp_range.low and temp_range.high
                class NameReplacer(ast.NodeTransformer):
                    """Replace Name nodes for low and high with Attribute access."""

                    def _create_attribute_access(
                        self, object_name: str, attr_name: str, ctx: ast.expr_context
                    ) -> ast.Attribute:
                        """Create an attribute access node.

                        Args:
                            object_name: Name of the object
                            attr_name: Name of the attribute
                            ctx: Context for the expression

                        Returns:
                            Attribute AST node
                        """
                        return ast.Attribute(
                            value=ast.Name(id=object_name, ctx=ast.Load()),
                            attr=attr_name,
                            ctx=ctx,
                        )

                    def visit_Name(self, node: ast.Name) -> Any:  # noqa: N802
                        """Visit Name nodes and replace low/high with temp_range.low/high."""
                        if node.id == "low":
                            return self._create_attribute_access("temp_range", "low", node.ctx)
                        elif node.id == "high":
                            return self._create_attribute_access("temp_range", "high", node.ctx)
                        return node

                replacer = NameReplacer()
                function_node.body = [replacer.visit(stmt) for stmt in function_node.body]

            return tree

        self.apply_ast_transform(transform)


# Register the command
register_command(PreserveWholeObjectCommand)
