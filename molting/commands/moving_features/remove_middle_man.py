"""Remove Middle Man refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import extract_all_methods

INIT_METHOD_NAME = "__init__"


class RemoveMiddleManCommand(BaseCommand):
    """Command to remove middle man delegation from a class."""

    name = "remove-middle-man"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for remove-middle-man: 'target'")

    def execute(self) -> None:
        """Apply remove-middle-man refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target"]
        source_code = self.file_path.read_text()

        tree = cst.parse_module(source_code)
        transformer = RemoveMiddleManTransformer(target_class)
        modified_tree = tree.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class RemoveMiddleManTransformer(cst.CSTTransformer):
    """Transforms code by removing middle man delegation."""

    def __init__(self, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to process
        """
        self.target_class = target_class
        self.delegate_field: str | None = None
        self.delegation_methods: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definitions to identify delegate field and methods."""
        if node.name.value == self.target_class:
            self._identify_delegate_and_methods(node)
        return True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class definitions to remove middle man."""
        if original_node.name.value != self.target_class:
            return updated_node

        # Transform the class body
        new_body: list[Any] = []
        for item in updated_node.body.body:
            # Skip delegation methods
            if isinstance(item, cst.FunctionDef):
                if item.name.value in self.delegation_methods:
                    continue
                # Transform method to rename fields
                transformed_method = self._transform_method(item)
                new_body.append(transformed_method)
            else:
                new_body.append(item)

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _transform_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a method to rename delegate fields.

        Args:
            method: The method to transform

        Returns:
            The transformed method
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return method

        new_stmts: list[Any] = []
        for stmt in method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                new_stmt = self._transform_statement(stmt)
                new_stmts.append(new_stmt)
            else:
                new_stmts.append(stmt)

        return method.with_changes(body=cst.IndentedBlock(body=new_stmts))

    def _transform_statement(self, stmt: cst.SimpleStatementLine) -> cst.SimpleStatementLine:
        """Transform statements to rename delegate fields.

        Args:
            stmt: The statement to transform

        Returns:
            The transformed statement
        """
        if not self.delegate_field:
            return stmt

        new_body = [self._transform_expression(expr) for expr in stmt.body]
        return stmt.with_changes(body=new_body) if new_body else stmt

    def _transform_expression(self, expr: cst.BaseSmallStatement) -> cst.BaseSmallStatement:
        """Transform a single expression, renaming delegate field if applicable.

        Args:
            expr: The expression to transform

        Returns:
            The transformed expression
        """
        if not isinstance(expr, cst.Assign):
            return expr

        target = expr.targets[0].target
        field_name = self._get_self_attribute_name(target)

        if not field_name or field_name != self.delegate_field:
            return expr

        # Rename field from private to public
        public_name = field_name.lstrip("_")
        new_target = target.with_changes(attr=cst.Name(public_name))
        return expr.with_changes(targets=[cst.AssignTarget(target=new_target)])

    def _identify_delegate_and_methods(self, class_def: cst.ClassDef) -> None:
        """Identify the delegate field and delegation methods.

        Args:
            class_def: The class definition to analyze
        """
        self._find_delegate_field(class_def)
        self._find_delegation_methods(class_def)

    def _find_delegate_field(self, class_def: cst.ClassDef) -> None:
        """Find the private delegate field in __init__ method.

        Args:
            class_def: The class definition to analyze
        """
        methods = extract_all_methods(class_def, exclude_init=False)
        for method in methods:
            if method.name.value != INIT_METHOD_NAME:
                continue

            self.delegate_field = self._extract_private_field_from_method(method)
            if self.delegate_field:
                break

    def _extract_private_field_from_method(self, method: cst.FunctionDef) -> str | None:
        """Extract the first private field assignment from a method.

        Args:
            method: The method to analyze

        Returns:
            The private field name if found, None otherwise
        """
        for stmt in method.body.body:
            if not isinstance(stmt, cst.SimpleStatementLine):
                continue

            for expr in stmt.body:
                if not isinstance(expr, cst.Assign):
                    continue

                field_name = self._get_self_attribute_name(expr.targets[0].target)
                if field_name and field_name.startswith("_"):
                    return field_name

        return None

    def _get_self_attribute_name(self, target: cst.BaseAssignTargetExpression) -> str | None:
        """Get the attribute name if target is self.field.

        Args:
            target: The assignment target

        Returns:
            The attribute name if it's a self attribute, None otherwise
        """
        if not isinstance(target, cst.Attribute):
            return None
        if not isinstance(target.value, cst.Name) or target.value.value != "self":
            return None
        return target.attr.value

    def _find_delegation_methods(self, class_def: cst.ClassDef) -> None:
        """Find delegation methods in the class.

        Args:
            class_def: The class definition to analyze
        """
        if not self.delegate_field:
            return

        methods = extract_all_methods(class_def, exclude_init=False)
        for method in methods:
            if self._is_delegation_method(method):
                self.delegation_methods.append(method.name.value)

    def _is_delegation_method(self, method: cst.FunctionDef) -> bool:
        """Check if a method is a delegation method.

        Args:
            method: The method to check

        Returns:
            True if the method is a delegation method
        """
        if not self.delegate_field:
            return False

        if self._is_magic_method(method):
            return False

        return_expr = self._extract_single_return_from_method(method)
        if not return_expr:
            return False

        return self._is_delegation_to_field(return_expr)

    def _is_magic_method(self, method: cst.FunctionDef) -> bool:
        """Check if method is a magic method.

        Args:
            method: The method to check

        Returns:
            True if the method name starts with underscore
        """
        return method.name.value.startswith("_")

    def _extract_single_return_from_method(
        self, method: cst.FunctionDef
    ) -> cst.BaseExpression | None:
        """Extract the return value from a method with a single return statement.

        Args:
            method: The method to analyze

        Returns:
            The return expression if it's a single return, None otherwise
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return None

        statements = method.body.body
        if len(statements) != 1:
            return None

        stmt = statements[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return None

        if len(stmt.body) != 1:
            return None

        expr = stmt.body[0]
        if not isinstance(expr, cst.Return):
            return None

        return expr.value

    def _is_delegation_to_field(self, expr: cst.BaseExpression | None) -> bool:
        """Check if expression is accessing the delegate field.

        Args:
            expr: The expression to check

        Returns:
            True if accessing self._field.something
        """
        if not expr:
            return False

        if not isinstance(expr, cst.Attribute):
            return False

        obj = expr.value
        if not isinstance(obj, cst.Attribute):
            return False

        if not isinstance(obj.value, cst.Name) or obj.value.value != "self":
            return False

        field_name = obj.attr.value
        return field_name == self.delegate_field


# Register the command
register_command(RemoveMiddleManCommand)
