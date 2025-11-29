"""Inline Method refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class InlineMethodCommand(BaseCommand):
    """Inline Method refactoring command.

    Replaces method calls with the method's body when the method body is just as clear
    as the method name. This refactoring simplifies code by eliminating unnecessary
    indirection and reducing the number of method definitions.

    The Inline Method refactoring is based on Martin Fowler's "Refactoring" patterns.
    It transforms a class by identifying a target method, extracting its body and
    return expression, inlining the method call at its call sites, and removing the
    original method definition.

    **When to use:**
    - When a method body is just as clear as its name, making the method unnecessary
    - When a method is used only once or very infrequently
    - When removing a method reduces unnecessary indirection
    - When you want to simplify a class by consolidating straightforward methods
    - When refactoring towards larger, more meaningful methods

    **Example:**
    Before:
        class Calculator:
            def get_total(self, price, tax_rate):
                return price + (price * tax_rate)

            def calculate_final_price(self, price, tax_rate):
                return self.get_total(price, tax_rate) * 1.1

    After:
        class Calculator:
            def calculate_final_price(self, price, tax_rate):
                return (price + (price * tax_rate)) * 1.1
    """

    name = "inline-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply inline-method refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target format: "ClassName::method_name"
        class_name, method_name = parse_target(target, expected_parts=2)

        # Read file
        source_code = self.file_path.read_text()

        # First pass: capture the method body
        module = cst.parse_module(source_code)
        collector = MethodBodyCollector(class_name, method_name)
        module.visit(collector)

        if collector.return_expression is None:
            raise ValueError(
                f"Method '{method_name}' not found in class '{class_name}' "
                "or does not have a return statement"
            )

        # Second pass: inline the method
        transformer = InlineMethodTransformer(
            class_name, method_name, collector.body_statements, collector.return_expression
        )
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class MethodBodyCollector(cst.CSTVisitor):
    """Collector to capture the method body."""

    def __init__(self, class_name: str, method_name: str) -> None:
        """Initialize the collector.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to inline
        """
        self.class_name = class_name
        self.method_name = method_name
        self.body_statements: list[cst.CSTNode] = []
        self.return_expression: cst.BaseExpression | None = None
        self.in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Leave class definition."""
        if node.name.value == self.class_name:
            self.in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to capture the method body."""
        if self.in_target_class and node.name.value == self.method_name:
            self._extract_body_and_return(node)

    def _extract_body_and_return(self, node: cst.FunctionDef) -> None:
        """Extract all body statements and the return expression from a method.

        Args:
            node: The function definition node
        """
        body = list(node.body.body)

        # Skip docstring if present
        start_idx = 0
        if body and isinstance(body[0], cst.SimpleStatementLine):
            first_stmt = body[0].body[0] if body[0].body else None
            if isinstance(first_stmt, cst.Expr) and isinstance(first_stmt.value, cst.SimpleString):
                start_idx = 1

        # Find and extract the return statement (should be last)
        if not body[start_idx:]:
            return

        last_stmt = body[-1]

        # Handle simple return statement on its own line
        if isinstance(last_stmt, cst.SimpleStatementLine) and len(last_stmt.body) == 1:
            if isinstance(last_stmt.body[0], cst.Return) and last_stmt.body[0].value:
                self.return_expression = last_stmt.body[0].value
                self.body_statements = body[start_idx:-1]
                return

        # If no explicit return found at end, return None
        return


class InlineMethodTransformer(cst.CSTTransformer):
    """Transforms a class by inlining a method."""

    def __init__(
        self,
        class_name: str,
        method_name: str,
        body_statements: list[cst.CSTNode],
        return_expression: cst.BaseExpression,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to inline
            body_statements: Statements to insert before the call site (excluding return)
            return_expression: The expression from the return statement
        """
        self.class_name = class_name
        self.method_name = method_name
        self.body_statements = body_statements
        self.return_expression = return_expression
        self.in_target_class = False
        self.insert_before_next_statement = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and remove the inlined method."""
        if original_node.name.value == self.class_name:
            self.in_target_class = False
            statements_without_inlined_method = [
                stmt
                for stmt in updated_node.body.body
                if not (isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.method_name)
            ]
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=tuple(statements_without_inlined_method))
            )
        return updated_node

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Insert body statements where the call was found."""
        if not self.in_target_class or original_node.name.value == self.method_name:
            return updated_node

        # Check if the original function body had a call to the target method
        if not self.body_statements:
            # No body statements to insert, simple case
            return updated_node

        # Check original for target call and find where it was
        new_body: list[cst.CSTNode] = []
        for orig_stmt, updated_stmt in zip(original_node.body.body, updated_node.body.body):
            if isinstance(orig_stmt, cst.BaseStatement) and self._statement_has_target_call(
                orig_stmt
            ):
                # Insert body statements before this statement
                new_body.extend(self.body_statements)
            new_body.append(updated_stmt)

        return updated_node.with_changes(body=updated_node.body.with_changes(body=tuple(new_body)))

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Leave call expression and replace method calls with return expression."""
        if self._is_target_method_call(updated_node):
            return self.return_expression
        return updated_node

    def _is_target_method_call(self, node: cst.Call) -> bool:
        """Check if a call node is a call to self.method_name().

        Args:
            node: The call node to check

        Returns:
            True if this is a call to the target method, False otherwise
        """
        if not isinstance(node.func, cst.Attribute):
            return False

        return (
            isinstance(node.func.value, cst.Name)
            and node.func.value.value == "self"
            and node.func.attr.value == self.method_name
        )

    def _statement_has_target_call(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement contains a call to the target method.

        Args:
            stmt: The statement to check

        Returns:
            True if the statement contains a call to the target method
        """

        class CallFinder(cst.CSTVisitor):
            def __init__(self, method_name: str) -> None:
                self.method_name = method_name
                self.found = False

            def visit_Call(self, node: cst.Call) -> None:  # noqa: N802
                if isinstance(node.func, cst.Attribute):
                    if (
                        isinstance(node.func.value, cst.Name)
                        and node.func.value.value == "self"
                        and node.func.attr.value == self.method_name
                    ):
                        self.found = True

        finder = CallFinder(self.method_name)
        # Create a dummy module to enable traversal
        stmt_to_check = cast(
            cst.SimpleStatementLine | cst.BaseCompoundStatement,
            stmt,
        )
        dummy_module = cst.Module(body=[stmt_to_check])
        dummy_module.visit(finder)
        return finder.found


# Register the command
register_command(InlineMethodCommand)
