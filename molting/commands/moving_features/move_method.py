"""Move Method refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_self_field_assignment, is_self_attribute, parse_target
from molting.core.code_generation_utils import create_parameter
from molting.core.visitors import MethodConflictChecker, SelfFieldCollector

# Global cache for multi-file refactoring
# Maps (source_class, method_name) -> (param_mapping, target_class_field, method_node)
_METHOD_INFO_CACHE: dict[
    tuple[str, str], tuple[dict[str, str], str | None, cst.FunctionDef | None]
] = {}


class MoveMethodCommand(BaseCommand):
    """Move a method from one class to another when it better belongs elsewhere.

    The Move Method refactoring relocates a method to the class that uses it most,
    improving encapsulation and reducing coupling. This is particularly useful when
    a method makes greater use of features in another class than its own class.

    **When to use:**
    - A method uses or is used by more features of another class
    - You want to reduce coupling between classes
    - A method would be more logically placed in another class
    - Moving the method would improve cohesion and code organization

    **Example:**
    Before:
        class Account:
            def __init__(self, account_type):
                self.account_type = account_type

            def overdraft_charge(self):
                # Uses account_type more than its own features
                if self.account_type.premium:
                    return 10
                return 20

        class AccountType:
            def __init__(self, premium=False):
                self.premium = premium

    After:
        class Account:
            def __init__(self, account_type):
                self.account_type = account_type

            def overdraft_charge(self):
                return self.account_type.overdraft_charge(self.account_type)

        class AccountType:
            def __init__(self, premium=False):
                self.premium = premium

            def overdraft_charge(self, account_type):
                if account_type.premium:
                    return 10
                return 20
    """

    name = "move-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("source", "to")

    def execute(self) -> None:
        """Apply move-method refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        source = self.params["source"]
        to_class = self.params["to"]

        source_class, method_name = parse_target(source, expected_parts=2)

        # Check if target class already has a method with the same name
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        conflict_checker = MethodConflictChecker(to_class, method_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Class '{to_class}' already has a method named '{method_name}'")

        # Get cached method info if available (from previous file in multi-file refactoring)
        cache_key = (source_class, method_name)
        cached_info = _METHOD_INFO_CACHE.get(cache_key)
        param_mapping = cached_info[0] if cached_info else {}
        target_class_field = cached_info[1] if cached_info else None
        cached_method = cached_info[2] if cached_info else None

        self.apply_libcst_transform(
            MoveMethodTransformer,
            source_class,
            method_name,
            to_class,
            param_mapping,
            target_class_field,
            cached_method,
        )


class DelegationFieldFinder(cst.CSTVisitor):
    """Finds the field used for delegation (self.field.something patterns)."""

    def __init__(self) -> None:
        """Initialize the finder."""
        self.delegation_field: str | None = None

    def visit_Attribute(self, node: cst.Attribute) -> None:  # noqa: N802
        """Look for self.field.something patterns."""
        # Check if this is self.field.something
        if (
            isinstance(node.value, cst.Attribute)
            and isinstance(node.value.value, cst.Name)
            and node.value.value.value == "self"
        ):
            # This is self.<field>.<something>, so <field> is the delegation field
            if self.delegation_field is None:
                self.delegation_field = node.value.attr.value


class MoveMethodTransformer(cst.CSTTransformer):
    """Transforms code by moving a method from one class to another."""

    def __init__(
        self,
        source_class: str,
        method_name: str,
        target_class: str,
        param_mapping: dict[str, str] | None = None,
        target_class_field: str | None = None,
        cached_method: cst.FunctionDef | None = None,
    ) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the class containing the method to move
            method_name: Name of the method to move
            target_class: Name of the class to move the method to
            param_mapping: Pre-computed parameter mapping (for multi-file mode)
            target_class_field: Field that holds the target class instance (for multi-file mode)
            cached_method: Cached method definition (for multi-file mode)
        """
        self.source_class = source_class
        self.method_name = method_name
        self.target_class = target_class
        self.method_to_move: cst.FunctionDef | None = cached_method
        self.target_class_field = target_class_field
        self.source_class_found = False
        self.target_class_found = False
        self._param_mapping: dict[str, str] = param_mapping or {}

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class definitions to move the method."""
        if original_node.name.value == self.source_class:
            self.source_class_found = True
            return self._process_source_class(updated_node)

        if original_node.name.value == self.target_class:
            self.target_class_found = True
            return self._process_target_class(updated_node)

        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Update call sites if this is a call to the moved method."""
        # Only update call sites if we're not in the source or target class
        # (those are handled by the class-level transformers)
        if not self.source_class_found and not self.target_class_found:
            return self._update_call_site(original_node, updated_node)
        return updated_node

    def _update_call_site(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Update a call site to use the moved method.

        Transforms: source_var.method_name(target_var, ...)
        To: target_var.method_name(source_var.field1, source_var.field2, ...)

        Args:
            original_node: The original call node
            updated_node: The updated call node

        Returns:
            The transformed call node, or the original if not a match
        """
        # Check if this is a call to our method
        if not isinstance(updated_node.func, cst.Attribute):
            return updated_node

        if updated_node.func.attr.value != self.method_name:
            return updated_node

        # We need param_mapping to know what fields to pass
        if not self._param_mapping:
            return updated_node

        # Extract the caller (e.g., 'customer' from 'customer.calculate_discount(order)')
        caller = updated_node.func.value

        # Extract the first argument (e.g., 'order' from 'customer.calculate_discount(order)')
        if not updated_node.args or len(updated_node.args) == 0:
            return updated_node

        first_arg = updated_node.args[0].value

        # Build new arguments: source_var.field for each field in param_mapping
        new_args = []
        for field_name in self._param_mapping.keys():
            new_arg = cst.Arg(
                value=cst.Attribute(
                    value=caller,
                    attr=cst.Name(field_name),
                )
            )
            new_args.append(new_arg)

        # Add remaining arguments (if any)
        if len(updated_node.args) > 1:
            new_args.extend(updated_node.args[1:])

        # Create the new call: target_var.method_name(new_args)
        new_call = updated_node.with_changes(
            func=cst.Attribute(
                value=first_arg,
                attr=cst.Name(self.method_name),
            ),
            args=new_args,
        )

        return new_call

    def _process_source_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Process the source class to find and replace the method.

        Args:
            node: The source class definition

        Returns:
            Updated class definition with the method replaced by a delegation call
        """
        updated_class_members: list[Any] = []
        method_found = False

        for item in node.body.body:
            if isinstance(item, cst.FunctionDef) and item.name.value == self.method_name:
                method_found = True
                self.method_to_move = item
                self.target_class_field = self._find_target_class_field(node)
                # Pre-compute parameter mapping for use in delegation method
                self._param_mapping = self._compute_param_mapping(item)

                # Cache method info for multi-file refactoring
                cache_key = (self.source_class, self.method_name)
                _METHOD_INFO_CACHE[cache_key] = (
                    self._param_mapping,
                    self.target_class_field,
                    self.method_to_move,
                )

                delegation_method = self._create_delegation_method(item)
                updated_class_members.append(delegation_method)
            else:
                updated_class_members.append(item)

        if not method_found:
            # In multi-file mode, the source class might not be in this file
            return node

        return node.with_changes(body=node.body.with_changes(body=tuple(updated_class_members)))

    def _process_target_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Process the target class to add the moved method.

        Args:
            node: The target class definition

        Returns:
            Updated class definition with the new method added
        """
        if self.method_to_move is None:
            return node

        transformed_method = self._transform_method_for_target()
        method_with_spacing = transformed_method.with_changes(
            leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
        )

        updated_members = tuple(list(node.body.body) + [method_with_spacing])
        return node.with_changes(body=node.body.with_changes(body=updated_members))

    def _find_target_class_field(self, node: cst.ClassDef) -> str | None:
        """Find the field that references the target class.

        This looks for a field that is used as a delegation target in the method,
        i.e., self.field.something patterns.

        Args:
            node: The source class definition

        Returns:
            The field name that holds the target class instance, or None if not found
        """
        # Look for self.field.something patterns in the method
        if self.method_to_move is None:
            return None
        delegation_finder = DelegationFieldFinder()
        self.method_to_move.visit(delegation_finder)

        return delegation_finder.delegation_field

    def _extract_field_from_init(
        self, init_method: cst.FunctionDef, exclude_fields: list[str]
    ) -> str | None:
        """Extract the field name from __init__ that holds the target class.

        Args:
            init_method: The __init__ method definition
            exclude_fields: Fields that are being passed as parameters (not the target field)

        Returns:
            The field name, or None if not found
        """
        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                result = find_self_field_assignment(stmt)
                if result:
                    field_name, value = result
                    # Skip fields that will be passed as parameters
                    if field_name in exclude_fields:
                        continue
                    # Only return fields that are assigned from a parameter (Name node)
                    if isinstance(value, cst.Name):
                        return field_name
        return None

    def _compute_param_mapping(self, method: cst.FunctionDef) -> dict[str, str]:
        """Compute the mapping from field names to clean parameter names.

        Args:
            method: The method being moved

        Returns:
            Dict mapping field names to clean parameter names
        """
        params_needed = self._collect_self_references(method)
        param_mapping = {}
        for param_name in params_needed:
            clean_name = param_name.lstrip("_") if param_name.startswith("_") else param_name
            param_mapping[param_name] = clean_name
        return param_mapping

    def _create_delegation_method(self, original_method: cst.FunctionDef) -> cst.FunctionDef:
        """Create a delegation method that calls the moved method.

        Args:
            original_method: The original method being moved

        Returns:
            A new method that delegates to the target class
        """
        if not hasattr(self, "_param_mapping"):
            self._param_mapping = self._compute_param_mapping(original_method)

        params_to_pass = self._collect_self_references(original_method)
        # Use the clean parameter names in the delegation call
        args = [
            cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name(param)))
            for param in params_to_pass
        ]

        # Determine whether the target object is a field or a parameter
        # Check if the first parameter (after self) exists - if so, it's likely the target object
        target_param_name = None
        if original_method.params and len(original_method.params.params) > 1:
            target_param_name = original_method.params.params[1].name.value

        # If there's a target class field, use it; otherwise use the parameter
        delegation_target: cst.BaseExpression
        if self.target_class_field:
            # Target is a field: self.account_type.method(args)
            delegation_target = cst.Attribute(
                value=cst.Name("self"),
                attr=cst.Name(self.target_class_field),
            )
        elif target_param_name:
            # Target is a parameter: order.method(args)
            delegation_target = cst.Name(target_param_name)
        else:
            raise ValueError(
                f"Could not find field or parameter referencing target class '{self.target_class}' "
                f"in source class '{self.source_class}'"
            )

        delegation_call = cst.Return(
            value=cst.Call(
                func=cst.Attribute(
                    value=delegation_target,
                    attr=cst.Name(self.method_name),
                ),
                args=args,
            )
        )

        # Extract docstring from original method body if present
        docstring_stmt = None
        if original_method.body and isinstance(original_method.body, cst.IndentedBlock):
            for stmt in original_method.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for item in stmt.body:
                        if isinstance(item, cst.Expr) and isinstance(item.value, cst.SimpleString):
                            docstring_stmt = stmt
                            break
                    if docstring_stmt:
                        break

        # Build delegation body
        # Keep the docstring if:
        # 1. Method has decorators, OR
        # 2. Target is a parameter (not a field) - multi-file case
        delegation_body_stmts = []
        if docstring_stmt and (original_method.decorators or not self.target_class_field):
            delegation_body_stmts.append(docstring_stmt)
        delegation_body_stmts.append(cst.SimpleStatementLine(body=[delegation_call]))

        delegation_body = cst.IndentedBlock(body=delegation_body_stmts)
        return original_method.with_changes(body=delegation_body)

    def _collect_self_references(self, method: cst.FunctionDef) -> list[str]:
        """Collect self.field references that need to be passed as parameters.

        Args:
            method: The method to analyze

        Returns:
            List of field names that are referenced
        """
        exclude_fields = {self.target_class_field} if self.target_class_field else set()
        collector = SelfFieldCollector(exclude_fields=exclude_fields)
        method.visit(collector)
        return collector.collected_fields

    def _remove_docstring_from_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Remove the docstring from a method body.

        Args:
            body: The method body

        Returns:
            The body without docstring
        """
        new_body_stmts = []
        docstring_found = False

        for stmt in body.body:
            # Skip the first string expression (docstring)
            if (
                not docstring_found
                and isinstance(stmt, cst.SimpleStatementLine)
                and len(stmt.body) == 1
            ):
                item = stmt.body[0]
                if isinstance(item, cst.Expr) and isinstance(item.value, cst.SimpleString):
                    docstring_found = True
                    continue

            new_body_stmts.append(stmt)

        return body.with_changes(body=tuple(new_body_stmts))

    def _transform_method_for_target(self) -> cst.FunctionDef:
        """Transform the method to work in the target class.

        Returns:
            The transformed method with parameters instead of self references
        """
        if self.method_to_move is None:
            raise ValueError("No method to move")

        params_needed = self._collect_self_references(self.method_to_move)

        # Create clean parameter names (strip leading underscores)
        param_mapping = {}
        new_params = [create_parameter("self")]
        for param_name in params_needed:
            clean_name = param_name.lstrip("_") if param_name.startswith("_") else param_name
            param_mapping[param_name] = clean_name
            new_params.append(create_parameter(clean_name))

        # Get the name of the first parameter (after self) - this is the target object
        target_param_name = None
        if self.method_to_move.params and len(self.method_to_move.params.params) > 1:
            target_param_name = self.method_to_move.params.params[1].name.value

        body_transformer = SelfReferenceReplacer(
            param_mapping, self.target_class_field, target_param_name
        )
        transformed_body = self.method_to_move.body.visit(body_transformer)

        # If method has decorators, remove docstring from moved method
        # If method has no decorators, keep the docstring
        if self.method_to_move.decorators and isinstance(transformed_body, cst.IndentedBlock):
            transformed_body = self._remove_docstring_from_body(transformed_body)

        return self.method_to_move.with_changes(
            params=cst.Parameters(params=new_params), body=transformed_body, decorators=()
        )


class SelfReferenceReplacer(cst.CSTTransformer):
    """Replaces self.field with parameter references and self.target_field.x with self.x."""

    def __init__(
        self,
        field_mapping: dict[str, str] | list[str],
        target_class_field: str | None = None,
        target_param_name: str | None = None,
    ) -> None:
        """Initialize the replacer.

        Args:
            field_mapping: Dict mapping field names to parameter names, or list of field names
            target_class_field: The field that holds the target class (to be replaced with self)
            target_param_name: The name of the parameter that holds the target object
                             (references to this should be replaced with self)
        """
        # Support both dict and list for backward compatibility
        if isinstance(field_mapping, dict):
            self.field_mapping = field_mapping
            self.fields_to_replace = list(field_mapping.keys())
        else:
            self.field_mapping = {name: name for name in field_mapping}
            self.fields_to_replace = field_mapping
        self.target_class_field = target_class_field
        self.target_param_name = target_param_name

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute | cst.Name:
        """Replace self.field with parameter name or self.target_field.x with self.x."""
        # Replace self.account_type.x with self.x
        if (
            isinstance(updated_node.value, cst.Attribute)
            and isinstance(updated_node.value.value, cst.Name)
            and updated_node.value.value.value == "self"
            and updated_node.value.attr.value == self.target_class_field
        ):
            return cst.Attribute(value=cst.Name("self"), attr=updated_node.attr)

        # Replace order.x with self.x (where order is the first parameter)
        if (
            self.target_param_name
            and isinstance(updated_node.value, cst.Name)
            and updated_node.value.value == self.target_param_name
        ):
            return cst.Attribute(value=cst.Name("self"), attr=updated_node.attr)

        # Replace self.field with parameter name
        if is_self_attribute(updated_node):
            field_name = updated_node.attr.value
            if field_name in self.field_mapping:
                param_name = self.field_mapping[field_name]
                return cst.Name(param_name)
        return updated_node


# Register the command
register_command(MoveMethodCommand)
