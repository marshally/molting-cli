"""Replace Parameter with Explicit Methods refactoring command."""

import ast

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_tree, parse_target


class ReplaceParameterWithExplicitMethodsCommand(BaseCommand):
    """Command to replace a parameter with explicit methods."""

    name = "replace-parameter-with-explicit-methods"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-parameter-with-explicit-methods refactoring using AST manipulation.

        Raises:
            ValueError: If method or parameter not found
        """
        target = self.params["target"]
        _, method_name, param_name = parse_target(target, expected_parts=3)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to replace a parameter with explicit methods.

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

            class_node, method_node = result

            param_index = None
            for i, arg in enumerate(method_node.args.args):
                if arg.arg == param_name:
                    param_index = i
                    break

            if param_index is None:
                raise ValueError(f"Parameter '{param_name}' not found in method '{method_name}'")

            parameter_values = self._extract_parameter_values(method_node, param_name)

            if not parameter_values:
                raise ValueError(
                    f"No parameter values found for '{param_name}' in method '{method_name}'"
                )

            new_methods = []
            for value in parameter_values:
                new_method = self._create_explicit_method(
                    method_node, param_name, param_index, value
                )
                new_methods.append(new_method)

            method_index = class_node.body.index(method_node)
            class_node.body.pop(method_index)

            for i, new_method in enumerate(new_methods):
                class_node.body.insert(method_index + i, new_method)

            return tree

        self.apply_ast_transform(transform)

    def _extract_parameter_values(self, method_node: ast.FunctionDef, param_name: str) -> list[str]:
        """Extract the values that the parameter is compared against.

        Args:
            method_node: The method node
            param_name: The parameter name

        Returns:
            List of parameter values (e.g., ["height", "width"])

        Raises:
            ValueError: If the method doesn't have the expected structure
        """
        values = []

        for stmt in method_node.body:
            if isinstance(stmt, ast.If):
                for if_node in self._iterate_if_chain(stmt):
                    value = self._extract_value_from_condition(if_node.test, param_name)
                    if value:
                        values.append(value)

        return values

    def _iterate_if_chain(self, if_stmt: ast.If) -> list[ast.If]:
        """Iterate through an if-elif chain.

        Args:
            if_stmt: The initial if statement

        Returns:
            List of all if nodes in the chain (including elif branches)
        """
        nodes = [if_stmt]
        current = if_stmt
        while current.orelse:
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                current = current.orelse[0]
                nodes.append(current)
            else:
                break
        return nodes

    def _extract_value_from_condition(self, condition: ast.expr, param_name: str) -> str | None:
        """Extract the value from a condition like 'name == "height"'.

        Args:
            condition: The condition expression
            param_name: The parameter name to look for

        Returns:
            The value being compared, or None if not found
        """
        if not isinstance(condition, ast.Compare):
            return None

        if not isinstance(condition.left, ast.Name) or condition.left.id != param_name:
            return None

        if len(condition.ops) != 1 or not isinstance(condition.ops[0], ast.Eq):
            return None

        if len(condition.comparators) != 1 or not isinstance(
            condition.comparators[0], ast.Constant
        ):
            return None

        value = condition.comparators[0].value
        if not isinstance(value, str):
            return None

        return value

    def _create_explicit_method(
        self,
        original_method: ast.FunctionDef,
        param_name: str,
        param_index: int,
        value: str,
    ) -> ast.FunctionDef:
        """Create a new explicit method for a specific parameter value.

        Args:
            original_method: The original method node
            param_name: The parameter name being replaced
            param_index: The index of the parameter
            value: The value for this explicit method

        Returns:
            The new method node
        """
        # Create the new method name (e.g., "set_height" from "set_value" and "height")
        method_prefix = original_method.name.rsplit("_", 1)[0]
        new_method_name = f"{method_prefix}_{value}"

        # Create new arguments list without the parameter being replaced
        new_args = [arg for i, arg in enumerate(original_method.args.args) if i != param_index]

        # Extract the body for this specific value
        new_body = self._extract_body_for_value(original_method, param_name, value)

        # Create the new method
        new_method = ast.FunctionDef(
            name=new_method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=new_args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=new_body,
            decorator_list=[],
        )

        return new_method

    def _extract_body_for_value(
        self, method_node: ast.FunctionDef, param_name: str, value: str
    ) -> list[ast.stmt]:
        """Extract the body statements for a specific parameter value.

        Args:
            method_node: The method node
            param_name: The parameter name
            value: The value to extract the body for

        Returns:
            List of statements for this value
        """
        for stmt in method_node.body:
            if isinstance(stmt, ast.If):
                for if_node in self._iterate_if_chain(stmt):
                    if self._extract_value_from_condition(if_node.test, param_name) == value:
                        return if_node.body

        return []


# Register the command
register_command(ReplaceParameterWithExplicitMethodsCommand)
