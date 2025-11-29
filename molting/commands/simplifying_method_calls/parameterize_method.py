"""Parameterize Method refactoring command."""

import ast

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_tree, parse_target


class ParameterizeMethodCommand(BaseCommand):
    """Parameterize Method refactoring: combine similar methods into a single parameterized method.

    The Parameterize Method refactoring takes multiple methods that perform similar operations
    with different literal values and consolidates them into a single method that accepts those
    values as parameters. This eliminates code duplication and makes the code more flexible
    and maintainable.

    This refactoring is based on Martin Fowler's "Refactoring" book and is a fundamental
    technique for reducing duplication and improving code clarity.

    **When to use:**
    - You have multiple methods that perform the same logic with different literal values
    - You want to eliminate code duplication across similar methods
    - You need a more flexible, configurable version of repeated method logic
    - You're preparing code for further refactoring by reducing method proliferation

    **Example:**
    Before:
        class Employee:
            def five_percent_raise(self):
                self.salary *= 1.05

            def ten_percent_raise(self):
                self.salary *= 1.10

    After:
        class Employee:
            def raise_salary(self, percentage):
                self.salary *= 1 + percentage / 100

            def five_percent_raise(self):
                self.raise_salary(5)

            def ten_percent_raise(self):
                self.raise_salary(10)
    """

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

            # Determine the type of refactoring (percentage or threshold-based)
            is_percentage_based = self._is_percentage_based(method_node1)

            if is_percentage_based:
                # Extract percentage values from multiplication-based methods
                parameter1 = self._extract_percentage(method_node1)
                parameter2 = self._extract_percentage(method_node2)
                attribute_name = self._extract_attribute_name(method_node1)
                new_method = self._create_parameterized_method(new_name, attribute_name)
            else:
                # Extract threshold values from comparison-based methods
                parameter1 = self._extract_threshold_attribute(method_node1)
                parameter2 = self._extract_threshold_attribute(method_node2)
                new_method = self._create_threshold_parameterized_method(new_name, method_node1)

            # Update the original methods to call the new method
            self._update_method_to_call_new(method_node1, new_name, parameter1, is_percentage_based)
            self._update_method_to_call_new(method_node2, new_name, parameter2, is_percentage_based)

            # Insert the new method after the __init__ method
            insertion_position = 0
            for i, node in enumerate(class_node.body):
                if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                    insertion_position = i
                    break

            class_node.body.insert(insertion_position + 1, new_method)

            return tree

        self.apply_ast_transform(transform)

    def _get_augmented_assignment(self, method_node: ast.FunctionDef) -> ast.AugAssign | ast.Assign:
        """Get the augmented assignment statement from a method.

        Args:
            method_node: The method node

        Returns:
            The augmented assignment or simple assignment statement

        Raises:
            ValueError: If the method doesn't have the expected structure
        """
        if not method_node.body:
            raise ValueError(f"Method '{method_node.name}' has empty body")

        stmt = method_node.body[0]

        # Direct augmented assignment case (e.g., self.salary *= 1.05)
        if isinstance(stmt, ast.AugAssign):
            return stmt

        # If statement case (e.g., if condition: self.field = value)
        if isinstance(stmt, ast.If) and stmt.body:
            # Look for assignment inside the if body
            for inner_stmt in stmt.body:
                if isinstance(inner_stmt, ast.Assign):
                    return inner_stmt
                if isinstance(inner_stmt, ast.AugAssign):
                    return inner_stmt

        raise ValueError(f"Method '{method_node.name}' doesn't have expected assignment")

    def _extract_percentage(self, method_node: ast.FunctionDef) -> int:
        """Extract the percentage value from a method like five_percent_raise.

        Args:
            method_node: The method node

        Returns:
            The percentage value (e.g., 5 for 1.05, 10 for 1.10)

        Raises:
            ValueError: If the method doesn't have the expected structure
        """
        stmt = self._get_augmented_assignment(method_node)

        if not isinstance(stmt.value, ast.Constant):
            raise ValueError(f"Method '{method_node.name}' doesn't have expected constant")

        # Convert 1.05 to 5, 1.10 to 10
        multiplier = stmt.value.value
        if not isinstance(multiplier, (int, float)):
            raise ValueError(
                f"Method '{method_node.name}' has non-numeric multiplier: {type(multiplier)}"
            )
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
        stmt = self._get_augmented_assignment(method_node)

        # Handle both AugAssign and Assign statements
        if isinstance(stmt, ast.AugAssign):
            if not isinstance(stmt.target, ast.Attribute):
                raise ValueError(f"Method '{method_node.name}' doesn't modify an attribute")
            return stmt.target.attr
        elif isinstance(stmt, ast.Assign):
            # For simple assignments, check the targets
            if stmt.targets and isinstance(stmt.targets[0], ast.Attribute):
                return stmt.targets[0].attr
            raise ValueError(f"Method '{method_node.name}' doesn't modify an attribute")
        else:
            raise ValueError(f"Method '{method_node.name}' doesn't have expected assignment")

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
        self,
        method_node: ast.FunctionDef,
        new_method_name: str,
        parameter,
        is_percentage_based: bool = True,
    ) -> None:
        """Update a method to call the new parameterized method.

        Args:
            method_node: The method node to update
            new_method_name: The name of the new method to call
            parameter: The parameter value to pass (int for percentage, str
                for threshold attribute)
            is_percentage_based: Whether this is percentage or threshold based
        """
        # For percentage: self.raise_salary(5)
        # For threshold: self.mark_stock_level(self.low_stock_threshold)
        if is_percentage_based:
            arg = ast.Constant(value=parameter)
        else:
            # parameter is an attribute name like "low_stock_threshold"
            arg = ast.Attribute(
                value=ast.Name(id="self", ctx=ast.Load()),
                attr=parameter,
                ctx=ast.Load(),
            )

        method_node.body = [
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=new_method_name,
                        ctx=ast.Load(),
                    ),
                    args=[arg],
                    keywords=[],
                )
            )
        ]

    def _is_percentage_based(self, method_node: ast.FunctionDef) -> bool:
        """Check if percentage-based (salary *= 1.XX) or threshold-based (if quantity <= XX).

        Args:
            method_node: The method to check

        Returns:
            True if percentage-based, False if threshold-based
        """
        # Check the first statement
        if not method_node.body:
            return False

        stmt = method_node.body[0]

        # Direct augmented assignment = percentage-based
        if isinstance(stmt, ast.AugAssign):
            return True

        # If statement = could be threshold-based
        return False

    def _extract_threshold_attribute(self, method_node: ast.FunctionDef) -> str:
        """Extract the threshold attribute name from a method.

        Args:
            method_node: The method node

        Returns:
            The attribute name used in the threshold (e.g., "low_stock_threshold")

        Raises:
            ValueError: If the method doesn't have the expected structure
        """
        if not method_node.body or not isinstance(method_node.body[0], ast.If):
            raise ValueError(f"Method '{method_node.name}' doesn't have if statement")

        if_stmt = method_node.body[0]

        # Look for a comparison in the if condition
        # Expecting something like: self.quantity <= self.low_stock_threshold
        if isinstance(if_stmt.test, ast.Compare):
            comparators = if_stmt.test.comparators
            if comparators and isinstance(comparators[0], ast.Attribute):
                return comparators[0].attr

        raise ValueError(f"Method '{method_node.name}' doesn't have expected threshold comparison")

    def _create_threshold_parameterized_method(
        self, method_name: str, original_method: ast.FunctionDef
    ) -> ast.FunctionDef:
        """Create a new parameterized method for threshold-based refactoring.

        Args:
            method_name: The name of the new method
            original_method: The original method to base the new one on

        Returns:
            The new method node
        """
        # Get the original if statement and copy it
        if not original_method.body or not isinstance(original_method.body[0], ast.If):
            raise ValueError(f"Method '{original_method.name}' doesn't have if statement")

        original_if = original_method.body[0]

        # Clone the if statement and modify the comparison to use the parameter
        new_if = self._replace_threshold_with_parameter(original_if)

        new_method = ast.FunctionDef(
            name=method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self"), ast.arg(arg="threshold")],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[new_if],
            decorator_list=[],
        )
        return new_method

    def _replace_threshold_with_parameter(self, if_stmt: ast.If) -> ast.If:
        """Replace the threshold attribute with a parameter in an if statement.

        Args:
            if_stmt: The if statement to modify

        Returns:
            A new if statement with the threshold replaced by a parameter
        """
        # Deep copy the if statement
        import copy

        new_if = copy.deepcopy(if_stmt)

        # Replace the comparator (right side of <=) with the parameter
        if isinstance(new_if.test, ast.Compare):
            if new_if.test.comparators:
                # Replace the first comparator with ast.Name("threshold")
                new_if.test.comparators[0] = ast.Name(id="threshold", ctx=ast.Load())

        return new_if


# Register the command
register_command(ParameterizeMethodCommand)
