"""Parameterize Method refactoring command."""

import ast

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_tree, parse_target


class ParameterizeMethodCommand(BaseCommand):
    """Command to parameterize similar methods."""

    name = "parameterize-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target1", "target2", "new_name")

    def execute(self) -> None:
        """Apply parameterize-method refactoring using AST manipulation.

        Raises:
            ValueError: If methods not found or target format is invalid
        """
        target1 = self.params["target1"]
        target2 = self.params["target2"]
        new_name = self.params["new_name"]

        _, method_name1 = parse_target(target1)
        _, method_name2 = parse_target(target2)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to parameterize similar methods.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If methods not found
            """
            result1 = find_method_in_tree(tree, method_name1)
            result2 = find_method_in_tree(tree, method_name2)

            if result1 is None:
                raise ValueError(f"Method '{method_name1}' not found in {self.file_path}")
            if result2 is None:
                raise ValueError(f"Method '{method_name2}' not found in {self.file_path}")

            class_node, method_node1 = result1
            _, method_node2 = result2

            # Extract the percentage values from the original methods
            # For five_percent_raise: self.salary *= 1.05 -> 5
            # For ten_percent_raise: self.salary *= 1.10 -> 10
            percentage1 = self._extract_percentage(method_node1)
            percentage2 = self._extract_percentage(method_node2)

            # Extract the attribute name being modified (e.g., "salary")
            attribute_name = self._extract_attribute_name(method_node1)

            # Create the new parameterized method
            new_method = self._create_parameterized_method(new_name, attribute_name)

            # Update the original methods to call the new method
            self._update_method_to_call_new(method_node1, new_name, percentage1)
            self._update_method_to_call_new(method_node2, new_name, percentage2)

            # Insert the new method after the __init__ method
            insertion_position = 0
            for i, node in enumerate(class_node.body):
                if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                    insertion_position = i
                    break

            class_node.body.insert(insertion_position + 1, new_method)

            return tree

        self.apply_ast_transform(transform)

    def _extract_percentage(self, method_node: ast.FunctionDef) -> int:
        """Extract the percentage value from a method like five_percent_raise.

        Args:
            method_node: The method node

        Returns:
            The percentage value (e.g., 5 for 1.05, 10 for 1.10)

        Raises:
            ValueError: If the method doesn't have the expected structure
        """
        if not method_node.body or len(method_node.body) != 1:
            raise ValueError(f"Method '{method_node.name}' has unexpected structure")

        stmt = method_node.body[0]
        if not isinstance(stmt, ast.AugAssign):
            raise ValueError(f"Method '{method_node.name}' doesn't have expected assignment")

        if not isinstance(stmt.value, ast.Constant):
            raise ValueError(f"Method '{method_node.name}' doesn't have expected constant")

        # Convert 1.05 to 5, 1.10 to 10
        multiplier = stmt.value.value
        percentage = int((multiplier - 1) * 100)
        return percentage

    def _extract_attribute_name(self, method_node: ast.FunctionDef) -> str:
        """Extract the attribute name being modified in the method.

        Args:
            method_node: The method node

        Returns:
            The attribute name (e.g., "salary")

        Raises:
            ValueError: If the method doesn't have the expected structure
        """
        if not method_node.body or len(method_node.body) != 1:
            raise ValueError(f"Method '{method_node.name}' has unexpected structure")

        stmt = method_node.body[0]
        if not isinstance(stmt, ast.AugAssign):
            raise ValueError(f"Method '{method_node.name}' doesn't have expected assignment")

        if not isinstance(stmt.target, ast.Attribute):
            raise ValueError(f"Method '{method_node.name}' doesn't modify an attribute")

        return stmt.target.attr

    def _create_parameterized_method(
        self, method_name: str, attribute_name: str
    ) -> ast.FunctionDef:
        """Create a new parameterized method.

        Args:
            method_name: The name of the new method
            attribute_name: The attribute name to modify

        Returns:
            The new method node
        """
        # Create: def raise_salary(self, percentage):
        #             self.salary *= 1 + percentage / 100
        new_method = ast.FunctionDef(
            name=method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self"), ast.arg(arg="percentage")],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[
                ast.AugAssign(
                    target=ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=attribute_name,
                        ctx=ast.Store(),
                    ),
                    op=ast.Mult(),
                    value=ast.BinOp(
                        left=ast.Constant(value=1),
                        op=ast.Add(),
                        right=ast.BinOp(
                            left=ast.Name(id="percentage", ctx=ast.Load()),
                            op=ast.Div(),
                            right=ast.Constant(value=100),
                        ),
                    ),
                )
            ],
            decorator_list=[],
        )
        return new_method

    def _update_method_to_call_new(
        self, method_node: ast.FunctionDef, new_method_name: str, percentage: int
    ) -> None:
        """Update a method to call the new parameterized method.

        Args:
            method_node: The method node to update
            new_method_name: The name of the new method to call
            percentage: The percentage value to pass
        """
        # Replace the body with: self.raise_salary(5)
        method_node.body = [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=new_method_name,
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value=percentage)],
                    keywords=[],
                )
            )
        ]


# Register the command
register_command(ParameterizeMethodCommand)
