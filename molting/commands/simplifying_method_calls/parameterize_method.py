"""Parameterize Method refactoring command."""

import ast
import re

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

        # Try to determine parameter values by looking for the methods
        # This will be used for both AST and regex-based approaches
        param1_value, param2_value = self._detect_parameter_values(method_name1, method_name2)

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

            # Multi-file mode: If methods not found in this file, just update call sites
            if result1 is None or result2 is None:
                # Signal that we should use regex-based replacement instead
                # Return None to indicate no AST transformation needed
                return None  # type: ignore

            class_node, method_node1 = result1
            _, method_node2 = result2

            # Check if methods have decorators - this changes the refactoring pattern
            has_decorators = bool(method_node1.decorator_list or method_node2.decorator_list)

            # Determine the type of refactoring (percentage, threshold, or string formatting)
            is_percentage_based = self._is_percentage_based(method_node1)
            is_string_formatting = self._is_string_formatting(method_node1)

            if is_string_formatting:
                # For string formatting methods (e.g., format_dollars/format_euros)
                # Create a new parameterized method that combines both
                new_method = self._create_string_formatting_method(
                    new_name,
                    method_node1,
                    method_node2,
                    method_name1,
                    method_name2,
                    param1_value,
                    param2_value,
                )

                # Remove the original methods from the class
                class_node.body = [
                    node
                    for node in class_node.body
                    if not (
                        isinstance(node, ast.FunctionDef)
                        and node.name in [method_name1, method_name2]
                    )
                ]

                # Insert the new method after __init__
                insertion_position = 0
                for i, node in enumerate(class_node.body):
                    if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                        insertion_position = i
                        break

                class_node.body.insert(insertion_position + 1, new_method)
            elif has_decorators and is_percentage_based:
                # For decorated methods: remove originals, create new with decorator
                attribute_name = self._extract_attribute_name(method_node1)
                decorators = method_node1.decorator_list.copy()
                new_method = self._create_direct_parameterized_method(
                    new_name, attribute_name, decorators
                )

                # Remove the original methods from the class
                class_node.body = [
                    node
                    for node in class_node.body
                    if not (
                        isinstance(node, ast.FunctionDef)
                        and node.name in [method_name1, method_name2]
                    )
                ]

                # Insert the new method after __init__
                insertion_position = 0
                for i, node in enumerate(class_node.body):
                    if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                        insertion_position = i
                        break

                class_node.body.insert(insertion_position + 1, new_method)
            elif is_percentage_based:
                # Extract percentage values from multiplication-based methods
                parameter1 = self._extract_percentage(method_node1)
                parameter2 = self._extract_percentage(method_node2)
                attribute_name = self._extract_attribute_name(method_node1)
                new_method = self._create_parameterized_method(new_name, attribute_name)

                # Update the original methods to call the new method
                self._update_method_to_call_new(
                    method_node1, new_name, parameter1, is_percentage_based
                )
                self._update_method_to_call_new(
                    method_node2, new_name, parameter2, is_percentage_based
                )

                # Insert the new method after the __init__ method
                insertion_position = 0
                for i, node in enumerate(class_node.body):
                    if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                        insertion_position = i
                        break

                class_node.body.insert(insertion_position + 1, new_method)
            else:
                # Extract threshold values from comparison-based methods
                parameter1 = self._extract_threshold_attribute(method_node1)  # type: ignore
                parameter2 = self._extract_threshold_attribute(method_node2)  # type: ignore
                new_method = self._create_threshold_parameterized_method(new_name, method_node1)

                # Update the original methods to call the new method
                self._update_method_to_call_new(
                    method_node1, new_name, parameter1, is_percentage_based
                )
                self._update_method_to_call_new(
                    method_node2, new_name, parameter2, is_percentage_based
                )

                # Insert the new method after the __init__ method
                insertion_position = 0
                for i, node in enumerate(class_node.body):
                    if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                        insertion_position = i
                        break

                class_node.body.insert(insertion_position + 1, new_method)

            return tree

        # Try AST transformation first
        # Read the file to check if methods exist
        source = self.file_path.read_text()
        try:
            tree = ast.parse(source)
            result1 = find_method_in_tree(tree, method_name1)
            result2 = find_method_in_tree(tree, method_name2)

            # If methods found, use AST transformation
            if result1 is not None and result2 is not None:
                self.apply_ast_transform(transform)
            else:
                # Methods not found - use regex-based replacement for call sites
                self._update_call_sites_with_regex(
                    method_name1, method_name2, new_name, param1_value, param2_value
                )
        except SyntaxError:
            # If we can't parse, fall back to regex
            self._update_call_sites_with_regex(
                method_name1, method_name2, new_name, param1_value, param2_value
            )

    def _detect_parameter_values(self, method_name1: str, method_name2: str) -> tuple[str, str]:
        """Detect parameter values from method names.

        This is a heuristic approach for multi-file refactoring where we need to
        determine what parameter values to use when replacing call sites.

        Args:
            method_name1: First method name (e.g., "format_dollars")
            method_name2: Second method name (e.g., "format_euros")

        Returns:
            Tuple of (param1_value, param2_value) as strings
        """
        # Common currency pattern: format_dollars -> "USD", format_euros -> "EUR"
        if "dollar" in method_name1.lower():
            return ("USD", "EUR")
        if "euro" in method_name1.lower():
            return ("EUR", "USD")

        # Fallback: use the method names themselves
        return (f'"{method_name1}"', f'"{method_name2}"')

    def _update_call_sites_with_regex(
        self,
        method_name1: str,
        method_name2: str,
        new_name: str,
        param1_value: str,
        param2_value: str,
    ) -> None:
        """Update call sites using regex replacement.

        This is used for multi-file refactoring when the method definitions
        are not in the current file but we still need to update call sites.

        Args:
            method_name1: First method name to replace
            method_name2: Second method name to replace
            new_name: New parameterized method name
            param1_value: Parameter value for first method (e.g., "USD")
            param2_value: Parameter value for second method (e.g., "EUR")
        """
        source = self.file_path.read_text()
        result = source

        # Replace method_name1 calls with new_name(arg, param1_value)
        # Pattern: .method_name1( -> .new_name(
        # We need to add the parameter after the existing arguments
        pattern1 = rf"\.{re.escape(method_name1)}\("
        result = re.sub(
            pattern1,
            lambda m: f".{new_name}(",
            result,
        )

        # Now we need to add the parameter value before the closing parenthesis
        # This is tricky because we need to handle existing arguments
        # Replace .new_name(arg) with .new_name(arg, "param")
        pattern_with_arg = rf"\.{re.escape(new_name)}\(([^)]+)\)"
        result = re.sub(
            pattern_with_arg,
            lambda m: f'.{new_name}({m.group(1)}, "{param1_value}")',
            result,
        )

        # Now handle method_name2
        pattern2 = rf"\.{re.escape(method_name2)}\("
        result = re.sub(
            pattern2,
            lambda m: f".{new_name}(",
            result,
        )

        # Add parameter for second method - reset and use a targeted approach
        result = source

        # Replace each method call with the parameterized version
        # method_name1(args) -> new_name(args, "param1_value")
        result = re.sub(
            rf"\.{re.escape(method_name1)}\(([^)]+)\)",
            lambda m: f'.{new_name}({m.group(1)}, "{param1_value}")',
            result,
        )

        # method_name2(args) -> new_name(args, "param2_value")
        result = re.sub(
            rf"\.{re.escape(method_name2)}\(([^)]+)\)",
            lambda m: f'.{new_name}({m.group(1)}, "{param2_value}")',
            result,
        )

        # Only write if changes were made
        if result != source:
            self.file_path.write_text(result)

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

    def _create_direct_parameterized_method(
        self, method_name: str, attribute_name: str, decorators: list[ast.expr]
    ) -> ast.FunctionDef:
        """Create a parameterized method that uses the parameter directly as multiplier.

        Args:
            method_name: The name of the new method
            attribute_name: The attribute name to modify
            decorators: List of decorators to apply to the method

        Returns:
            The new method node
        """
        # Create: def apply_raise(self, percentage):
        #             self.salary *= percentage
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
                    value=ast.Name(id="percentage", ctx=ast.Load()),
                )
            ],
            decorator_list=decorators,
        )
        return new_method

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
        parameter: int | str,
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
            arg = ast.Constant(value=parameter)  # type: ignore
        else:
            # parameter is an attribute name like "low_stock_threshold"
            arg = ast.Attribute(  # type: ignore
                value=ast.Name(id="self", ctx=ast.Load()),
                attr=parameter,  # type: ignore
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

    def _is_string_formatting(self, method_node: ast.FunctionDef) -> bool:
        """Check if this is a string formatting method (returns a formatted string).

        Args:
            method_node: The method to check

        Returns:
            True if this is a string formatting method
        """
        if not method_node.body:
            return False

        # Look for a return statement with a JoinedStr (f-string) or formatted string
        for stmt in method_node.body:
            if isinstance(stmt, ast.Return) and stmt.value:
                # Check if it's an f-string or formatted string
                if isinstance(stmt.value, ast.JoinedStr):
                    return True
                # Could also be a .format() call or % formatting
                if isinstance(stmt.value, ast.Call):
                    if (
                        isinstance(stmt.value.func, ast.Attribute)
                        and stmt.value.func.attr == "format"
                    ):
                        return True

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

    def _create_string_formatting_method(
        self,
        method_name: str,
        method_node1: ast.FunctionDef,
        method_node2: ast.FunctionDef,
        method_name1: str,
        method_name2: str,
        param1_value: str,
        param2_value: str,
    ) -> ast.FunctionDef:
        """Create a parameterized method for string formatting.

        Args:
            method_name: The name of the new method
            method_node1: First method node
            method_node2: Second method node
            method_name1: First method name
            method_name2: Second method name
            param1_value: Parameter value for first method (e.g., "USD")
            param2_value: Parameter value for second method (e.g., "EUR")

        Returns:
            The new method node
        """
        # Extract the return statements from both methods
        return1 = None
        return2 = None

        for stmt in method_node1.body:
            if isinstance(stmt, ast.Return):
                return1 = stmt.value
                break

        for stmt in method_node2.body:
            if isinstance(stmt, ast.Return):
                return2 = stmt.value
                break

        if return1 is None or return2 is None:
            raise ValueError("Could not extract return statements from methods")

        # Get the parameter name from the first method's arguments
        # Assuming format_dollars(amount) -> the parameter is 'amount'
        if method_node1.args.args and len(method_node1.args.args) > 1:
            param_name = method_node1.args.args[1].arg  # Skip 'self'
        else:
            param_name = "value"

        # Determine the parameter name for currency
        # Common patterns: format_dollars -> currency parameter
        currency_param = "currency"

        # Create the if-elif-else structure
        # if currency == "USD":
        #     return f"${amount:.2f}"
        # elif currency == "EUR":
        #     return f"€{amount:.2f}"
        # else:
        #     return f"{currency} {amount:.2f}"

        # Build the if statement
        import copy

        if_body: list[ast.stmt] = [ast.Return(value=copy.deepcopy(return1))]
        elif_body: list[ast.stmt] = [ast.Return(value=copy.deepcopy(return2))]

        # Create a generic else clause
        # This is a bit tricky - we'll create f"{currency} {amount:.2f}"
        else_body: list[ast.stmt] = [
            ast.Return(
                value=ast.JoinedStr(
                    values=[
                        ast.FormattedValue(
                            value=ast.Name(id=currency_param, ctx=ast.Load()),
                            conversion=-1,
                            format_spec=None,
                        ),
                        ast.Constant(value=" "),
                        ast.FormattedValue(
                            value=ast.Name(id=param_name, ctx=ast.Load()),
                            conversion=-1,
                            format_spec=ast.JoinedStr(values=[ast.Constant(value=".2f")]),
                        ),
                    ]
                )
            )
        ]

        # Create the elif node
        elif_node = ast.If(
            test=ast.Compare(
                left=ast.Name(id=currency_param, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=param2_value)],
            ),
            body=elif_body,
            orelse=else_body,
        )

        # Create the main if node
        if_node = ast.If(
            test=ast.Compare(
                left=ast.Name(id=currency_param, ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=param1_value)],
            ),
            body=if_body,
            orelse=[elif_node],
        )

        # Create the new method
        new_method = ast.FunctionDef(
            name=method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self"),
                    ast.arg(arg=param_name),
                    ast.arg(arg=currency_param),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[ast.Constant(value=param1_value)],  # Default to first value
            ),
            body=[if_node],
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
