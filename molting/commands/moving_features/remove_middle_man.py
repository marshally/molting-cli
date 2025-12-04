"""Remove Middle Man refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.call_site_updater import CallSiteUpdater, Reference
from molting.core.symbol_context import SymbolContext

INIT_METHOD_NAME = "__init__"


class RemoveMiddleManCommand(BaseCommand):
    """Remove Middle Man refactoring: eliminate excessive delegation and expose delegates directly.

    The Remove Middle Man refactoring removes methods that simply delegate to another object.
    This refactoring applies when a class has become a "middle man" - doing excessive simple
    delegation that clutters the interface. By removing these delegating methods, clients call
    the delegate directly, simplifying the class and reducing unnecessary abstraction layers.

    This is the inverse of the Hide Delegate refactoring. While Hide Delegate helps encapsulate
    implementation details by hiding delegate objects, Remove Middle Man reverses this when the
    delegation becomes too pervasive and the middle man class loses its value.

    **When to use:**
    - A class has many delegating methods that simply pass through to an internal object
    - Clients need to know about both the middle man and the delegate object anyway
    - The delegating methods don't add significant business logic or value
    - You want to simplify a class interface that has become cluttered with pass-through methods

    **Example:**
    Before:
        class Department:
            def __init__(self, manager):
                self._manager = manager

            def get_manager_name(self):
                return self._manager.name

            def get_manager_budget(self):
                return self._manager.budget

        # Client code
        dept = Department(manager)
        print(dept.get_manager_name())
        print(dept.get_manager_budget())

    After:
        class Department:
            def __init__(self, manager):
                self.manager = manager

        # Client code
        dept = Department(manager)
        print(dept.manager.name)
        print(dept.manager.budget)
    """

    name = "remove-middle-man"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply remove-middle-man refactoring using libCST.

        Supports both single-file and multi-file refactoring:
        - In single-file mode: target is the class name
        - In multi-file mode: target is the filename, source is the class name

        Raises:
            ValueError: If transformation cannot be applied
        """
        # Determine if we're in multi-file mode
        target_param = self.params["target"]
        source_param = self.params.get("source")

        if source_param:
            # Multi-file mode: target is file, source is class
            target_class = source_param
            target_file = self.file_path.parent / target_param
        else:
            # Single-file mode: target is class, current file is the target
            target_class = target_param
            target_file = self.file_path

        # In multi-file mode, get delegation info from the target file FIRST
        # (before any modifications are written) so we know what to update
        delegation_transformer = None
        if source_param:
            # Read the target file to get delegation info
            target_source = target_file.read_text()
            target_tree = cst.parse_module(target_source)
            target_transformer = RemoveMiddleManTransformer(target_class)
            target_tree.visit(target_transformer)
            delegation_transformer = target_transformer

        # Transform the current file
        source_code = self.file_path.read_text()
        tree = cst.parse_module(source_code)
        transformer = RemoveMiddleManTransformer(target_class)
        modified_tree = tree.visit(transformer)

        # Only write if changes were made
        if modified_tree.code != source_code:
            self.file_path.write_text(modified_tree.code)

        # In single-file mode, use the transformer from the current file
        if not delegation_transformer:
            delegation_transformer = transformer

        # Update call sites for all removed delegation methods
        if delegation_transformer.delegate_field and delegation_transformer.delegation_methods:
            directory = self.file_path.parent
            updater = CallSiteUpdater(directory)

            # Get the public name of the delegate field (without leading underscore)
            public_field_name = delegation_transformer.delegate_field.lstrip("_")

            # Update each delegation method's call sites
            for method_name, delegated_attr in delegation_transformer.delegation_mapping.items():
                is_method = delegation_transformer.delegation_is_method.get(method_name, False)
                self._update_method_call_sites(
                    updater, method_name, public_field_name, delegated_attr, is_method
                )

    def _update_method_call_sites(
        self,
        updater: CallSiteUpdater,
        method_name: str,
        field_name: str,
        delegated_attr: str,
        is_method_delegation: bool,
    ) -> None:
        """Update all call sites for a removed delegation method.

        Args:
            updater: The CallSiteUpdater to use
            method_name: Name of the removed delegation method
            field_name: Name of the public delegate field
            delegated_attr: Name of the attribute/method being delegated to
            is_method_delegation: True if delegates to a method, False if to a field
        """

        def transform_call_site(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform method call to direct delegate access.

            Transforms:
            - obj.get_manager() -> obj.department.manager (field access)
            - obj.calculate_gross_pay() -> obj.compensation.calculate_gross_pay() (method call)
            """
            if isinstance(node, cst.Call) and isinstance(node.func, cst.Attribute):
                # node.func.value is the object being called on
                base_obj = node.func.value

                # Build the delegate access expression
                delegate_access = cst.Attribute(
                    value=cst.Attribute(value=base_obj, attr=cst.Name(field_name)),
                    attr=cst.Name(delegated_attr),
                )

                # If this delegates to a method, preserve the call; otherwise return attr
                if is_method_delegation:
                    # Preserve the call: obj.compensation.calculate_gross_pay()
                    return cst.Call(func=delegate_access, args=node.args)
                else:
                    # Remove the call: obj.department.manager (no parens)
                    return delegate_access
            return node

        updater.update_all(method_name, SymbolContext.METHOD_CALL, transform_call_site)


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
        self.delegation_mapping: dict[str, str] = {}  # method_name -> delegated_attr
        self.delegation_is_method: dict[
            str, bool
        ] = {}  # method_name -> True if delegates to method

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

        First identifies delegation patterns, then determines which field is the delegate.

        Args:
            class_def: The class definition to analyze
        """
        # First pass: find candidate delegation methods and their delegate fields
        delegate_fields = set()
        for item in class_def.body.body:
            if isinstance(item, cst.FunctionDef):
                delegate_field = self._get_delegate_field_from_method(item)
                if delegate_field:
                    delegate_fields.add(delegate_field)

        # Choose the most common delegate field (or first if tie)
        if delegate_fields:
            self.delegate_field = sorted(delegate_fields)[0]

        # Second pass: identify all delegation methods for this field
        self._find_delegation_methods(class_def)

    def _get_delegate_field_from_method(self, method: cst.FunctionDef) -> str | None:
        """Extract the delegate field name from a delegation method.

        Args:
            method: The method to analyze

        Returns:
            The delegate field name if this is a delegation method, None otherwise
        """
        if self._is_magic_method(method):
            return None

        return_expr = self._extract_single_return_from_method(method)
        if not return_expr:
            return None

        # Check for delegation pattern: self.field.attr or self.field.method()
        delegate_field = self._extract_delegate_field_from_expr(return_expr)
        return delegate_field

    def _extract_delegate_field_from_expr(self, expr: cst.BaseExpression | None) -> str | None:
        """Extract the delegate field name from a return expression.

        Args:
            expr: The expression to check

        Returns:
            The delegate field name if found, None otherwise
        """
        if not expr:
            return None

        # Handle method calls: self.field.method()
        if isinstance(expr, cst.Call):
            if not isinstance(expr.func, cst.Attribute):
                return None
            obj = expr.func.value
            if isinstance(obj, cst.Attribute):
                if isinstance(obj.value, cst.Name) and obj.value.value == "self":
                    return obj.attr.value

        # Handle attribute access: self.field.attribute
        if isinstance(expr, cst.Attribute):
            obj = expr.value
            if isinstance(obj, cst.Attribute):
                if isinstance(obj.value, cst.Name) and obj.value.value == "self":
                    return obj.attr.value

        return None

    def _find_delegate_field(self, class_def: cst.ClassDef) -> None:
        """Find the private delegate field in __init__ method.

        Args:
            class_def: The class definition to analyze
        """
        for item in class_def.body.body:
            if not isinstance(item, cst.FunctionDef):
                continue
            if item.name.value != INIT_METHOD_NAME:
                continue

            self.delegate_field = self._extract_private_field_from_method(item)
            if self.delegate_field:
                break

    def _extract_private_field_from_method(self, method: cst.FunctionDef) -> str | None:
        """Extract the first delegate field assignment from a method.

        Prioritizes private fields (starting with _) but will accept any field
        if no private field is found, to support cases where the field is already public.

        Args:
            method: The method to analyze

        Returns:
            The delegate field name if found, None otherwise
        """
        first_field = None
        for stmt in method.body.body:
            if not isinstance(stmt, cst.SimpleStatementLine):
                continue

            for expr in stmt.body:
                if not isinstance(expr, cst.Assign):
                    continue

                field_name = self._get_self_attribute_name(expr.targets[0].target)
                if not field_name:
                    continue

                # Prefer private fields
                if field_name.startswith("_"):
                    return field_name

                # Remember first field as fallback
                if first_field is None:
                    first_field = field_name

        return first_field

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

        for item in class_def.body.body:
            if isinstance(item, cst.FunctionDef):
                result = self._get_delegation_info(item)
                if result:
                    delegated_attr, is_method_call = result
                    self.delegation_methods.append(item.name.value)
                    self.delegation_mapping[item.name.value] = delegated_attr
                    self.delegation_is_method[item.name.value] = is_method_call

    def _get_delegation_info(self, method: cst.FunctionDef) -> tuple[str, bool] | None:
        """Get delegation info if this is a delegation method.

        Args:
            method: The method to check

        Returns:
            Tuple of (delegated_attr_name, is_method_call) or None if not a delegation method
        """
        if not self.delegate_field:
            return None

        if self._is_magic_method(method):
            return None

        return_expr = self._extract_single_return_from_method(method)
        if not return_expr:
            return None

        return self._extract_delegation_info(return_expr)

    def _get_delegated_attribute(self, method: cst.FunctionDef) -> str | None:
        """Get the delegated attribute name if this is a delegation method.

        Args:
            method: The method to check

        Returns:
            The name of the delegated attribute, or None if not a delegation method
        """
        result = self._get_delegation_info(method)
        return result[0] if result else None

    def _is_delegation_method(self, method: cst.FunctionDef) -> bool:
        """Check if a method is a delegation method.

        Args:
            method: The method to check

        Returns:
            True if the method is a delegation method
        """
        return self._get_delegated_attribute(method) is not None

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

        Skips docstrings when looking for the return statement.

        Args:
            method: The method to analyze

        Returns:
            The return expression if it's a single return, None otherwise
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return None

        statements = method.body.body

        # Filter out docstrings (Expr nodes with string values)
        non_docstring_stmts: list[cst.BaseStatement] = []
        for stmt in statements:
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                    expr_value = stmt.body[0].value
                    # Skip if it's a string literal (docstring)
                    if isinstance(
                        expr_value, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)
                    ):
                        continue
                non_docstring_stmts.append(stmt)
            else:
                non_docstring_stmts.append(stmt)

        # Now check if there's exactly one non-docstring statement
        if len(non_docstring_stmts) != 1:
            return None

        stmt = non_docstring_stmts[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return None

        if len(stmt.body) != 1:
            return None

        expr = stmt.body[0]
        if not isinstance(expr, cst.Return):
            return None

        return expr.value

    def _extract_delegation_info(self, expr: cst.BaseExpression | None) -> tuple[str, bool] | None:
        """Extract delegation info from a return expression.

        Args:
            expr: The expression to check

        Returns:
            Tuple of (delegated_attr_name, is_method_call) or None
        """
        if not expr:
            return None

        # Handle method calls: self._field.method()
        if isinstance(expr, cst.Call):
            if not isinstance(expr.func, cst.Attribute):
                return None
            # Extract the method name
            method_name = expr.func.attr.value
            # Check if it's called on self._field
            obj = expr.func.value
            if not isinstance(obj, cst.Attribute):
                return None
            if not isinstance(obj.value, cst.Name) or obj.value.value != "self":
                return None
            field_name = obj.attr.value
            if field_name != self.delegate_field:
                return None
            return (method_name, True)  # True = delegates to a method

        # Handle attribute access: self._field.attribute
        if isinstance(expr, cst.Attribute):
            obj = expr.value
            if not isinstance(obj, cst.Attribute):
                return None
            if not isinstance(obj.value, cst.Name) or obj.value.value != "self":
                return None
            field_name = obj.attr.value
            if field_name != self.delegate_field:
                return None
            # Return the attribute being accessed on the delegate
            return (expr.attr.value, False)  # False = delegates to a field

        return None

    def _is_delegation_to_field(self, expr: cst.BaseExpression | None) -> bool:
        """Check if expression is accessing the delegate field.

        Args:
            expr: The expression to check

        Returns:
            True if accessing self._field.something
        """
        return self._extract_delegation_info(expr) is not None


# Register the command
register_command(RemoveMiddleManCommand)
