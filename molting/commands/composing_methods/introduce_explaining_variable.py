"""Introduce Explaining Variable refactoring command."""

from typing import cast

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target_with_line
from molting.core.visitors import VariableConflictChecker


@register_command
class IntroduceExplainingVariableCommand(BaseCommand):
    """Extract complex expressions into temporary variables with meaningful names.

    The Introduce Explaining Variable refactoring breaks down complex expressions
    by assigning them to temporary variables with names that clearly describe their
    purpose. This improves code readability and makes complex logic easier to
    understand and debug.

    **When to use:**
    - An expression is difficult to understand at first glance
    - The same complex expression appears multiple times in the function
    - You want to document the intent of a calculation or condition
    - A complex expression would benefit from a descriptive name to clarify its role

    **Example:**

    Before:
        def calculate_price(quantity, unit_price, discount_rate):
            return quantity * unit_price * (1 - discount_rate) + (quantity * unit_price * 0.1)

    After:
        def calculate_price(quantity, unit_price, discount_rate):
            base_price = quantity * unit_price
            return base_price * (1 - discount_rate) + (base_price * 0.1)
    """

    name = "introduce-explaining-variable"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Supports two targeting modes:
        1. Line-based: target="function_name#L<line>"
        2. Expression-based: in_function="function_name", expression="<code>"

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Always require name
        self.validate_required_params("name")

        # Check for either target OR (in_function + expression)
        has_target = "target" in self.params
        has_expression_mode = "in_function" in self.params and "expression" in self.params

        if not has_target and not has_expression_mode:
            raise ValueError(
                f"Missing required parameters for {self.name}: "
                "either 'target' or both 'in_function' and 'expression' must be provided"
            )

    def execute(self) -> None:
        """Apply introduce-explaining-variable refactoring using libCST.

        Raises:
            ValueError: If function or expression not found
        """
        variable_name = self.params["name"]
        replace_all = self.params.get("replace_all", False)

        # Read file
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Determine targeting mode and find the expression
        if "target" in self.params:
            # Line-based targeting: "function_name#L<line>"
            target = self.params["target"]
            function_name, _, line_spec = parse_target_with_line(target)
            target_line = int(line_spec.lstrip("L"))

            wrapper = metadata.MetadataWrapper(module)
            line_collector = ExpressionCollector(function_name, target_line)
            wrapper.visit(line_collector)

            if line_collector.best_expression is None:
                raise ValueError(
                    f"Could not find expression at line {target_line} in function '{function_name}'"
                )

            target_expression = line_collector.best_expression
            expression_line = line_collector.best_line
        else:
            # Expression-based targeting: in_function + expression
            function_name = self.params["in_function"]
            expression_str = self.params["expression"]

            wrapper = metadata.MetadataWrapper(module)
            string_collector = ExpressionByStringCollector(function_name, expression_str)
            wrapper.visit(string_collector)

            if string_collector.found_expression is None:
                raise ValueError(
                    f"Could not find expression '{expression_str}' in function '{function_name}'"
                )

            target_expression = string_collector.found_expression
            expression_line = string_collector.found_line

        # Check for name conflicts before applying transformation
        conflict_checker = VariableConflictChecker(function_name, variable_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(
                f"Variable '{variable_name}' already exists in function '{function_name}'"
            )

        # Apply transformation
        wrapper = metadata.MetadataWrapper(module)
        transformer = IntroduceExplainingVariableTransformer(
            function_name,
            variable_name,
            target_expression,
            expression_line,
            replace_all=replace_all,
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ExpressionCollector(cst.CSTVisitor):
    """Collector to find the best expression to extract."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, function_name: str, target_line: int) -> None:
        """Initialize the collector.

        Args:
            function_name: Name of the function containing the expression
            target_line: Minimum line number to search from (1-indexed)
        """
        self.function_name = function_name
        self.target_line = target_line
        self.best_expression: cst.BaseExpression | None = None
        self.best_line: int = 0
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to track if we're in the target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Leave function definition."""
        if node.name.value == self.function_name:
            self.in_target_function = False

    def _check_expression(self, node: cst.BaseExpression) -> None:
        """Check if this expression should be extracted.

        We want the OUTERMOST expression on the target line. In leave_ order,
        the outermost is visited LAST (children first). So we keep updating
        best_expression to get the outermost.
        """
        if not self.in_target_function:
            return

        try:
            pos = self.get_metadata(metadata.PositionProvider, node)
            line = pos.start.line

            # Only consider expressions that start on the target line exactly
            if line != self.target_line:
                return

            # Always update - the last one (outermost) wins
            self.best_expression = node
            self.best_line = line
        except KeyError:
            pass

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> bool:  # noqa: N802
        """Visit binary operation - continue to children."""
        return True

    def leave_BinaryOperation(self, node: cst.BinaryOperation) -> None:  # noqa: N802
        """After visiting children, check if this whole binop should be extracted.

        Only consider multiply chains (not add/subtract).
        """
        if isinstance(node.operator, cst.Multiply):
            self._check_expression(node)

    def leave_Call(self, node: cst.Call) -> None:  # noqa: N802
        """After visiting children, check if call should be extracted.

        Calls are checked in leave_ to compete with multiplies for "outermost".
        """
        self._check_expression(node)


class ExpressionByStringCollector(cst.CSTVisitor):
    """Collector to find expressions by their source code string."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, function_name: str, expression_str: str) -> None:
        """Initialize the collector.

        Args:
            function_name: Name of the function containing the expression
            expression_str: The source code of the expression to find
        """
        self.function_name = function_name
        # Normalize the expression string by parsing and unparsing
        self.target_expression = cst.parse_expression(expression_str)
        self.found_expression: cst.BaseExpression | None = None
        self.found_line: int = 0
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to track if we're in the target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Leave function definition."""
        if node.name.value == self.function_name:
            self.in_target_function = False

    def _check_expression(self, node: cst.BaseExpression) -> None:
        """Check if this expression matches the target expression string."""
        if not self.in_target_function:
            return

        # Already found - only want first occurrence
        if self.found_expression is not None:
            return

        # Compare structurally (ignoring whitespace differences)
        if node.deep_equals(self.target_expression):
            self.found_expression = node
            try:
                pos = self.get_metadata(metadata.PositionProvider, node)
                self.found_line = pos.start.line
            except KeyError:
                self.found_line = 0

    def leave_BinaryOperation(self, node: cst.BinaryOperation) -> None:  # noqa: N802
        """Check binary operations for matches."""
        self._check_expression(node)

    def leave_Call(self, node: cst.Call) -> None:  # noqa: N802
        """Check call expressions for matches."""
        self._check_expression(node)


class IntroduceExplainingVariableTransformer(cst.CSTTransformer):
    """Transforms code by extracting expressions into explaining variables."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        function_name: str,
        variable_name: str,
        target_expression: cst.BaseExpression,
        target_line: int,
        *,
        replace_all: bool = False,
    ) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function containing the expression
            variable_name: Name for the new variable
            target_expression: The expression to extract (for reference)
            target_line: Line where the target expression starts
            replace_all: If True, replace all occurrences of the expression
        """
        self.function_name = function_name
        self.variable_name = variable_name
        self.target_expression = target_expression
        self.target_line = target_line
        self.replace_all = replace_all
        self.in_target_function = False
        self.replaced = False
        self.captured_expression: cst.BaseExpression | None = None
        # Track whether we expect to replace a BinaryOperation (Multiply) or a Call
        self.expect_multiply = isinstance(target_expression, cst.BinaryOperation) and isinstance(
            target_expression.operator, cst.Multiply
        )
        self.expect_call = isinstance(target_expression, cst.Call)
        # Track depth of multiply operations on target line
        self.multiply_depth = 0

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definition to track if we're in the target function."""
        if node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and insert variable assignment."""
        if original_node.name.value != self.function_name:
            return updated_node

        self.in_target_function = False

        if not self.replaced or self.captured_expression is None:
            return updated_node

        # Build the new assignment statement
        new_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.variable_name))],
                    value=self.captured_expression,
                )
            ]
        )

        # Find the return statement and insert before it
        new_body: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.SimpleStatementLine):
                for inner in stmt.body:
                    if isinstance(inner, cst.Return):
                        new_body.append(new_assignment)
                        break
            new_body.append(stmt)

        return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))

    def _is_on_target_line(self, node: cst.BaseExpression) -> bool:
        """Check if this node starts on the target line."""
        if not self.in_target_function:
            return False

        try:
            pos = self.get_metadata(metadata.PositionProvider, node)
            return pos.start.line == self.target_line
        except KeyError:
            return False

    def _expressions_equal(self, node: cst.BaseExpression, target: cst.BaseExpression) -> bool:
        """Check if two expressions are structurally equal (ignoring whitespace)."""
        return node.deep_equals(target)

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> bool:  # noqa: N802
        """Track entry into multiply operations on target line."""
        if isinstance(node.operator, cst.Multiply) and self._is_on_target_line(node):
            self.multiply_depth += 1
        return True

    def leave_BinaryOperation(  # noqa: N802
        self, original_node: cst.BinaryOperation, updated_node: cst.BinaryOperation
    ) -> cst.BaseExpression:
        """Replace binary operation with variable name if it matches target.

        We need to replace only the OUTERMOST multiply chain on the target line.
        We track depth: increment on visit, decrement on leave. Only replace when
        depth becomes 0 (we're leaving the outermost multiply).

        When replace_all=True, also replace other occurrences of the same expression.
        """
        if not self.in_target_function:
            return updated_node

        if not isinstance(original_node.operator, cst.Multiply):
            return updated_node

        # Check if this matches the target expression for replace_all
        if (
            self.replace_all
            and self.captured_expression is not None
            and self._expressions_equal(original_node, self.target_expression)
        ):
            return cst.Name(self.variable_name)

        if not self._is_on_target_line(original_node):
            return updated_node

        # Decrement depth
        self.multiply_depth -= 1

        # Only replace at the outermost level (depth == 0)
        if self.multiply_depth == 0 and self.expect_multiply and not self.replaced:
            self.replaced = True
            self.captured_expression = updated_node
            return cst.Name(self.variable_name)

        return updated_node

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Replace call expression with variable name if it matches target.

        Only replace if we're expecting a Call (not a BinaryOperation).
        """
        if not self.expect_call:
            # We don't expect a call, skip
            return updated_node

        if self.replaced:
            return updated_node

        if not self._is_on_target_line(original_node):
            return updated_node

        self.replaced = True
        self.captured_expression = updated_node
        return cst.Name(self.variable_name)
