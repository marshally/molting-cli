"""Inline Class refactoring command."""

from pathlib import Path
from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    extract_init_field_assignments,
    find_class_in_module,
    find_self_field_assignment,
)
from molting.core.call_site_updater import CallSiteUpdater, Reference
from molting.core.symbol_context import SymbolContext
from molting.core.visitors import DelegatingMethodChecker, MethodConflictChecker

INIT_METHOD_NAME = "__init__"


class InlineClassCommand(BaseCommand):
    """Move features from one class into another and remove the empty class.

    The Inline Class refactoring moves all features (fields and methods) from a class into another
    class, and then removes the now-empty source class. This is the reverse of Extract Class and
    is useful when a class has become too simple or its responsibilities have been consolidated
    into another class.

    **When to use:**
    - A class isn't doing very much and has minimal behavior
    - All of a class's features are used primarily by another class
    - A class was created as part of a refactoring that is no longer necessary
    - You want to simplify your codebase by removing unnecessary abstractions

    **Example:**

    Before:
        class Person:
            def __init__(self, name, telephone_number):
                self.name = name
                self.office_telephone = OfficePhone(telephone_number)

        class OfficePhone:
            def __init__(self, number):
                self.number = number

            def get_area_code(self):
                return self.number[:3]

            def get_number(self):
                return self.number

    After:
        class Person:
            def __init__(self, name, telephone_number):
                self.name = name
                self.office_phone_number = telephone_number

            def get_area_code(self):
                return self.office_phone_number[:3]

            def get_number(self):
                return self.office_phone_number
    """

    name = "inline-class"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("source_class", "into")

    def execute(self) -> None:
        """Apply inline-class refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        source_class = self.params["source_class"]
        target_class = self.params["into"]

        # Check for method name conflicts between source and target classes
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Find source class and get its method names and field names
        source_class_def = find_class_in_module(module, source_class)
        target_class_def = find_class_in_module(module, target_class)

        # For multi-file support, we need to discover delegate_field, source_methods,
        # source_fields, and source_class_def even if the classes aren't in the current file.
        # We'll scan the directory to find this information.
        (
            delegate_field,
            source_methods,
            source_fields,
            discovered_source_class_def,
        ) = self._discover_class_info(source_class, target_class, module, source_class_def)

        # Use the discovered source class definition if we didn't find it locally
        if not source_class_def and discovered_source_class_def:
            source_class_def = discovered_source_class_def

        # Validate method conflicts only if both classes exist in this file
        if source_class_def and target_class_def and delegate_field:
            self._validate_no_conflicts(module, target_class, source_methods, delegate_field)

        # Only apply transformation if source or target class exists in this file
        # For multi-file refactoring, some files may only have call sites
        if source_class_def or target_class_def:
            self.apply_libcst_transform(
                InlineClassTransformer,
                source_class,
                target_class,
                source_class_def,
                source_methods,
                source_fields,
                delegate_field,
            )

        # Update call sites for the inlined class across all files in the directory
        # This needs to happen for every file processed, even if it only has call sites
        if delegate_field and (source_methods or source_fields):
            directory = self.file_path.parent
            updater = CallSiteUpdater(directory)
            field_prefix = self._compute_prefix_from_field(delegate_field, source_class)

            # Update method call sites
            for method_name in source_methods:
                self._update_method_call_sites(updater, delegate_field, method_name)

            # Update field attribute access sites
            for field_name in source_fields:
                inlined_field_name = field_prefix + field_name
                self._update_field_access_sites(
                    updater, delegate_field, field_name, inlined_field_name
                )

            # Inline temporary variables that reference the delegate field
            # (e.g., tel = person.office_telephone)
            self._inline_delegate_field_assignments(
                directory, delegate_field, source_fields, field_prefix
            )

    def _discover_class_info(
        self,
        source_class: str,
        target_class: str,
        module: cst.Module,
        source_class_def: cst.ClassDef | None,
    ) -> tuple[str | None, list[str], set[str], cst.ClassDef | None]:
        """Discover delegate field, source methods, source fields, and source class def.

        For multi-file refactoring, this scans the directory to find the information
        even if the classes aren't in the current file.

        Args:
            source_class: Name of the source class
            target_class: Name of the target class
            module: The current module
            source_class_def: The source class definition if found in current file

        Returns:
            Tuple of (delegate_field, source_methods, source_fields, source_class_def)
        """
        delegate_field = self._find_delegate_field(module, target_class, source_class)
        source_methods: list[str] = []
        source_fields: set[str] = set()

        # If we found info in the current file, use it
        if source_class_def:
            for stmt in source_class_def.body.body:
                if isinstance(stmt, cst.FunctionDef):
                    if stmt.name.value != "__init__":
                        source_methods.append(stmt.name.value)
                    else:
                        field_assignments = extract_init_field_assignments(stmt)
                        source_fields.update(field_assignments.keys())
            return delegate_field, source_methods, source_fields, source_class_def

        # Otherwise, scan the directory to find the class definitions
        # This supports multi-file refactoring where classes may be in different files
        directory = self.file_path.parent
        external_source_class_def: cst.ClassDef | None = None

        for file_path in directory.glob("*.py"):
            if file_path == self.file_path:
                continue  # Already checked this file
            try:
                other_source = file_path.read_text()
                other_module = cst.parse_module(other_source)

                # Look for delegate field in other files
                if not delegate_field:
                    delegate_field = self._find_delegate_field(
                        other_module, target_class, source_class
                    )

                # Look for source class in other files
                other_source_class = find_class_in_module(other_module, source_class)
                if other_source_class and not source_methods:
                    external_source_class_def = other_source_class
                    for stmt in other_source_class.body.body:
                        if isinstance(stmt, cst.FunctionDef):
                            if stmt.name.value != "__init__":
                                source_methods.append(stmt.name.value)
                            else:
                                field_assignments = extract_init_field_assignments(stmt)
                                source_fields.update(field_assignments.keys())

                # Stop if we found everything
                if delegate_field and source_methods:
                    break
            except Exception:
                # Skip files that can't be parsed
                continue

        return delegate_field, source_methods, source_fields, external_source_class_def

    def _validate_no_conflicts(
        self,
        module: cst.Module,
        target_class: str,
        source_methods: list[str],
        delegate_field: str,
    ) -> None:
        """Validate that there are no method name conflicts.

        Args:
            module: The parsed module
            target_class: Name of the target class
            source_methods: List of method names from source class
            delegate_field: Name of the delegate field

        Raises:
            ValueError: If there are conflicting method names
        """
        for method_name in source_methods:
            conflict_checker = MethodConflictChecker(target_class, method_name)
            module.visit(conflict_checker)
            if conflict_checker.has_conflict:
                # Check if it's just a delegating method (not a true conflict)
                delegating_checker = DelegatingMethodChecker(
                    target_class, method_name, delegate_field
                )
                module.visit(delegating_checker)
                if not delegating_checker.is_delegating:
                    raise ValueError(
                        f"Class '{target_class}' already has a method named " f"'{method_name}'"
                    )

    def _find_delegate_field(
        self, module: cst.Module, target_class: str, source_class: str
    ) -> str | None:
        """Find the field in target class that holds a reference to source class.

        Args:
            module: The parsed module
            target_class: Name of the target class
            source_class: Name of the source class being inlined

        Returns:
            The field name if found, None otherwise
        """
        target_class_def = find_class_in_module(module, target_class)
        if not target_class_def:
            return None

        for stmt in target_class_def.body.body:
            if not isinstance(stmt, cst.FunctionDef):
                continue
            if stmt.name.value != INIT_METHOD_NAME:
                continue
            if not isinstance(stmt.body, cst.IndentedBlock):
                continue

            for body_stmt in stmt.body.body:
                if isinstance(body_stmt, cst.SimpleStatementLine):
                    result = find_self_field_assignment(body_stmt)
                    if result:
                        field_name, value = result
                        if self._is_source_class_instantiation(value, source_class):
                            return field_name
        return None

    def _is_source_class_instantiation(self, value: cst.BaseExpression, source_class: str) -> bool:
        """Check if a value is an instantiation of the source class.

        Args:
            value: The expression to check
            source_class: Name of the source class

        Returns:
            True if the value is a Call to the source class constructor
        """
        if isinstance(value, cst.Call):
            if isinstance(value.func, cst.Name):
                return value.func.value == source_class
        return False

    def _compute_prefix_from_field(self, field_name: str, source_class_name: str) -> str:
        """Compute the prefix from a delegation field name.

        Args:
            field_name: The delegation field name (e.g., "office_telephone")
            source_class_name: Name of the source class being inlined

        Returns:
            The prefix to use (e.g., "office_")
        """
        # Check if the field name is essentially just the source class name in snake_case
        # e.g., "phone_number" matches "PhoneNumber"
        import re

        # Convert source class name to snake_case
        source_class_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", source_class_name).lower()

        # If the delegate field name matches the source class in snake_case, no prefix
        if field_name == source_class_snake:
            return ""

        # Otherwise, use the standard prefix logic
        if "_" in field_name:
            parts = field_name.rsplit("_", 1)
            return parts[0] + "_"
        return ""

    def _update_method_call_sites(
        self, updater: CallSiteUpdater, delegate_field: str, method_name: str
    ) -> None:
        """Update all call sites for a method that was inlined.

        Transforms: obj.delegate_field.method() -> obj.method()

        Args:
            updater: The CallSiteUpdater to use
            delegate_field: Name of the delegate field being removed
            method_name: Name of the method being inlined
        """

        def transform_call_site(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform method call to remove delegate field access.

            Transforms: obj.office_telephone.get_telephone_number() -> obj.get_telephone_number()
            """
            if isinstance(node, cst.Call) and isinstance(node.func, cst.Attribute):
                # node.func is the attribute being called
                # (e.g., office_telephone.get_telephone_number)
                # Check if it's delegate_field.method_name
                if isinstance(node.func.value, cst.Attribute):
                    # Check if this is obj.delegate_field.method_name()
                    if (
                        node.func.value.attr.value == delegate_field
                        and node.func.attr.value == method_name
                    ):
                        # Replace with obj.method_name()
                        new_func = cst.Attribute(
                            value=node.func.value.value, attr=cst.Name(method_name)
                        )
                        return node.with_changes(func=new_func)
            return node

        updater.update_all(method_name, SymbolContext.METHOD_CALL, transform_call_site)

    def _update_field_access_sites(
        self, updater: CallSiteUpdater, delegate_field: str, source_field: str, inlined_field: str
    ) -> None:
        """Update all access sites for a field that was inlined.

        Transforms: obj.delegate_field.source_field -> obj.inlined_field

        Args:
            updater: The CallSiteUpdater to use
            delegate_field: Name of the delegate field being removed
            source_field: Name of the field in the source class
            inlined_field: Name of the inlined field in the target class
        """

        def transform_access_site(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform field access to use inlined field.

            Transforms: obj.office_telephone.area_code -> obj.office_area_code
            """
            if isinstance(node, cst.Attribute):
                # Check if this is obj.delegate_field.source_field
                if isinstance(node.value, cst.Attribute):
                    if node.value.attr.value == delegate_field and node.attr.value == source_field:
                        # Replace with obj.inlined_field
                        return cst.Attribute(value=node.value.value, attr=cst.Name(inlined_field))
            return node

        updater.update_all(source_field, SymbolContext.ATTRIBUTE_ACCESS, transform_access_site)

    def _inline_delegate_field_assignments(
        self, directory: Path, delegate_field: str, source_fields: set[str], field_prefix: str
    ) -> None:
        """Inline assignments that reference the delegate field.

        Transforms code like:
            tel = person.office_telephone
            return tel.area_code

        Into:
            return person.office_area_code

        Args:
            directory: Directory containing the code
            delegate_field: Name of the delegate field being removed
            source_fields: Set of field names from the source class
            field_prefix: Prefix for inlined fields
        """
        # Find all Python files in the directory
        for file_path in directory.rglob("*.py"):
            if file_path.is_file():
                try:
                    source_code = file_path.read_text()
                    module = cst.parse_module(source_code)

                    # Apply the inlining transformation
                    transformer = DelegateFieldInliner(delegate_field, source_fields, field_prefix)
                    modified_module = module.visit(transformer)

                    # Write back if changed
                    if modified_module != module:
                        file_path.write_text(modified_module.code)
                except Exception:
                    # Skip files that can't be parsed or processed
                    pass


class InlineClassTransformer(cst.CSTTransformer):
    """Transforms classes to inline source class into target class."""

    def __init__(
        self,
        source_class: str,
        target_class: str,
        external_source_class_def: cst.ClassDef | None,
        source_method_names: list[str],
        source_field_names: set[str],
        delegate_field_name: str | None,
    ) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the class to be inlined
            target_class: Name of the class to inline into
            external_source_class_def: Source class definition from another file (if any)
            source_method_names: List of method names from the source class
            source_field_names: Set of field names from the source class
            delegate_field_name: Name of the delegate field in target class
        """
        self.source_class = source_class
        self.target_class = target_class
        self.source_class_def: cst.ClassDef | None = None
        self.source_fields: dict[str, cst.BaseExpression] = {}
        self.source_methods: list[cst.FunctionDef] = []
        self.field_prefix = ""
        # For multi-file support: pre-computed information
        self.external_source_class_def = external_source_class_def
        self.external_source_method_names = source_method_names
        self.external_source_field_names = source_field_names
        self.external_delegate_field = delegate_field_name

    def visit_Module(self, node: cst.Module) -> bool:  # noqa: N802
        """Visit module to find and analyze source class."""
        self.source_class_def = find_class_in_module(node, self.source_class)
        if self.source_class_def:
            self._extract_source_features(self.source_class_def)
        elif self.external_source_class_def:
            # Use the external source class definition if we don't have a local one
            self.source_class_def = self.external_source_class_def
            self._extract_source_features(self.external_source_class_def)

        target_class_def = find_class_in_module(node, self.target_class)
        if target_class_def:
            # Try to determine field prefix from this file
            self._determine_field_prefix(target_class_def)
            # If we didn't find it locally but have external info, use that
            if not self.field_prefix and self.external_delegate_field:
                self.field_prefix = self._compute_prefix_from_field(self.external_delegate_field)

        return True

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and remove the source class and its imports."""
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            skip_stmt = False

            # Skip the source class definition if it exists in this file
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.source_class:
                    skip_stmt = True

            # Skip imports of the source class
            if isinstance(stmt, cst.SimpleStatementLine):
                for body_item in stmt.body:
                    if isinstance(body_item, (cst.Import, cst.ImportFrom)):
                        if self._imports_source_class(body_item):
                            skip_stmt = True
                            break

            if not skip_stmt:
                new_body.append(stmt)

        return updated_node.with_changes(body=tuple(new_body))

    def _imports_source_class(self, import_node: cst.Import | cst.ImportFrom) -> bool:
        """Check if an import statement imports the source class.

        Args:
            import_node: The import node to check

        Returns:
            True if the import imports the source class
        """
        if isinstance(import_node, cst.ImportFrom):
            # Check for: from module import SourceClass
            if isinstance(import_node.names, cst.ImportStar):
                return False
            for name in import_node.names:
                if isinstance(name.name, cst.Name):
                    if name.name.value == self.source_class:
                        return True
        elif isinstance(import_node, cst.Import):
            # Check for: import SourceClass
            for name in import_node.names:
                if isinstance(name.name, cst.Name):
                    if name.name.value == self.source_class:
                        return True
                elif isinstance(name.name, cst.Attribute):
                    # Handle dotted imports like import package.SourceClass
                    if name.name.attr.value == self.source_class:
                        return True
        return False

    def _get_source_method_names(self) -> set[str]:
        """Get names of methods from source class (excluding __init__).

        Returns:
            Set of method names from the source class
        """
        return {m.name.value for m in self.source_methods if m.name.value != INIT_METHOD_NAME}

    def _build_target_class_body(
        self, class_body: tuple[cst.BaseStatement, ...], source_method_names: set[str]
    ) -> list[cst.BaseStatement]:
        """Build the new body for the target class.

        Args:
            class_body: The original class body statements
            source_method_names: Names of methods being inlined

        Returns:
            List of statements for the new class body
        """
        new_body_stmts: list[cst.BaseStatement] = []
        inlined_methods_added: set[str] = set()

        for stmt in class_body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD_NAME:
                    new_body_stmts.append(self._transform_init_method(stmt))
                elif stmt.name.value in source_method_names:
                    # This is a delegating method - replace it with the inlined version
                    inlined_method = self._get_inlined_method_by_name(stmt.name.value)
                    if inlined_method:
                        new_body_stmts.append(inlined_method)
                        inlined_methods_added.add(stmt.name.value)
                else:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        # Add any remaining inlined methods that weren't replacements
        for method in self.source_methods:
            if (
                method.name.value != INIT_METHOD_NAME
                and method.name.value not in inlined_methods_added
            ):
                transformed_method = self._transform_method(method)
                new_body_stmts.append(transformed_method)

        return new_body_stmts

    def _get_inlined_method_by_name(self, method_name: str) -> cst.FunctionDef | None:
        """Get an inlined method by name from the source class.

        Args:
            method_name: Name of the method to find

        Returns:
            The transformed method if found, None otherwise
        """
        for method in self.source_methods:
            if method.name.value == method_name:
                return self._transform_method(method)
        return None

    def _process_target_class_statement(
        self, stmt: cst.BaseStatement, source_method_names: set[str]
    ) -> cst.BaseStatement | None:
        """Process a statement from the target class body.

        Transforms __init__ methods and removes delegating methods from source class.

        Args:
            stmt: The statement to process
            source_method_names: Names of methods being inlined

        Returns:
            The processed statement or None to skip it
        """
        if isinstance(stmt, cst.FunctionDef):
            if stmt.name.value == INIT_METHOD_NAME:
                return self._transform_init_method(stmt)
            elif stmt.name.value in source_method_names:
                return None  # Skip delegating methods

        return stmt

    def _add_inlined_methods(self, body_stmts: list[cst.BaseStatement]) -> None:
        """Add transformed methods from source class to target class body.

        Args:
            body_stmts: List of body statements to append to
        """
        for method in self.source_methods:
            if method.name.value != INIT_METHOD_NAME:
                self._add_inlined_method(method, body_stmts)

    def _add_inlined_method(
        self, method: cst.FunctionDef, body_stmts: list[cst.BaseStatement]
    ) -> None:
        """Add a single transformed method to the target class body.

        Args:
            method: The method to transform and add
            body_stmts: List of body statements to append to
        """
        transformed_method = self._transform_method(method)
        body_stmts.append(transformed_method)

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and inline source class if this is the target."""
        if original_node.name.value != self.target_class:
            return updated_node

        source_method_names = self._get_source_method_names()
        new_body_stmts = self._build_target_class_body(
            cast(tuple[cst.BaseStatement, ...], updated_node.body.body), source_method_names
        )

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _is_source_class_instantiation(self, value: cst.BaseExpression) -> bool:
        """Check if a value is an instantiation of the source class.

        Args:
            value: The expression to check

        Returns:
            True if the value is a Call to the source class constructor
        """
        if isinstance(value, cst.Call):
            if isinstance(value.func, cst.Name):
                return value.func.value == self.source_class
        return False

    def _extract_source_features(self, class_def: cst.ClassDef) -> None:
        """Extract fields and methods from source class.

        Args:
            class_def: The source class definition
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                self._process_source_method(stmt)

    def _process_source_method(self, method: cst.FunctionDef) -> None:
        """Process a method from the source class.

        Collects the method and extracts field assignments if it's __init__.

        Args:
            method: The method definition to process
        """
        self.source_methods.append(method)
        if method.name.value == INIT_METHOD_NAME:
            self.source_fields = extract_init_field_assignments(method)

    def _compute_prefix_from_field(self, field_name: str) -> str:
        """Compute the prefix from a delegation field name.

        Args:
            field_name: The delegation field name (e.g., "office_telephone")

        Returns:
            The prefix to use (e.g., "office_")
        """
        # Check if the field name is essentially just the source class name in snake_case
        # e.g., "phone_number" matches "PhoneNumber"
        import re

        # Convert source class name to snake_case
        source_class_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", self.source_class).lower()

        # If the delegate field name matches the source class in snake_case, no prefix
        if field_name == source_class_snake:
            return ""

        # Otherwise, use the standard prefix logic
        if "_" in field_name:
            parts = field_name.rsplit("_", 1)
            return parts[0] + "_"
        return ""

    def _determine_field_prefix(self, target_class_def: cst.ClassDef) -> None:
        """Determine the prefix to use for inlined fields.

        Args:
            target_class_def: The target class definition
        """
        init_method = self._find_init_method(target_class_def)
        if init_method:
            self._extract_prefix_from_init(init_method)

    def _find_init_method(self, class_def: cst.ClassDef) -> cst.FunctionDef | None:
        """Find the __init__ method in a class definition.

        Args:
            class_def: The class definition to search

        Returns:
            The __init__ method if found, None otherwise
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == INIT_METHOD_NAME:
                if isinstance(stmt.body, cst.IndentedBlock):
                    return stmt
        return None

    def _extract_prefix_from_init(self, init_method: cst.FunctionDef) -> None:
        """Extract the field prefix from source class instantiation in __init__.

        Args:
            init_method: The __init__ method to analyze
        """
        if not isinstance(init_method.body, cst.IndentedBlock):
            return

        for body_stmt in init_method.body.body:
            if isinstance(body_stmt, cst.SimpleStatementLine):
                self._check_and_set_prefix_for_statement(body_stmt)

    def _check_and_set_prefix_for_statement(self, stmt: cst.SimpleStatementLine) -> None:
        """Check if statement assigns source class instance and set prefix.

        Args:
            stmt: The statement to check
        """
        result = find_self_field_assignment(stmt)
        if result:
            field_name, value = result
            if self._is_source_class_instantiation(value):
                self.field_prefix = self._compute_prefix_from_field(field_name)

    def _transform_init_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform the __init__ method to inline source class fields.

        Args:
            node: The __init__ method to transform

        Returns:
            The transformed __init__ method
        """
        new_stmts: list[cst.BaseStatement] = []

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                transformed_stmts = self._transform_init_statement(stmt)
                new_stmts.extend(transformed_stmts)

        return node.with_changes(body=cst.IndentedBlock(body=new_stmts))

    def _transform_init_statement(self, stmt: cst.BaseStatement) -> list[cst.BaseStatement]:
        """Transform a single statement from __init__ method.

        Replaces source class instantiation with inlined field assignments.

        Args:
            stmt: The statement to transform

        Returns:
            List of transformed statements (may be one or multiple)
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return [stmt]

        result = find_self_field_assignment(stmt)
        if not result:
            return [stmt]

        field_name, value = result
        if not self._is_source_class_instantiation(value):
            return [stmt]

        # Replace source class instantiation with inlined field assignments
        return self._create_inlined_field_assignments()

    def _create_inlined_field_assignments(self) -> list[cst.BaseStatement]:
        """Create assignments for all inlined source class fields.

        Returns:
            List of assignment statements for inlined fields
        """
        assignments: list[cst.BaseStatement] = []

        for field_name, field_value in self.source_fields.items():
            new_field_name = self.field_prefix + field_name
            assignment = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(new_field_name),
                                )
                            )
                        ],
                        value=field_value,
                    )
                ]
            )
            assignments.append(assignment)

        return assignments

    def _transform_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a method from source class to use inlined fields.

        Args:
            method: The method to transform

        Returns:
            The transformed method
        """
        transformer = FieldReferenceTransformer(self.source_fields, self.field_prefix)
        return cast(cst.FunctionDef, method.visit(transformer))


class FieldReferenceTransformer(cst.CSTTransformer):
    """Transforms field references in methods."""

    def __init__(self, source_fields: dict[str, cst.BaseExpression], field_prefix: str) -> None:
        """Initialize the transformer.

        Args:
            source_fields: Dictionary of source class fields
            field_prefix: Prefix to add to field names
        """
        self.source_fields = source_fields
        self.field_prefix = field_prefix

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Leave attribute and update field references."""
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "self":
                field_name = updated_node.attr.value
                if field_name in self.source_fields:
                    new_field_name = self.field_prefix + field_name
                    return updated_node.with_changes(attr=cst.Name(new_field_name))

        return updated_node


class DelegateFieldInliner(cst.CSTTransformer):
    """Inlines temporary variables that reference the delegate field."""

    def __init__(self, delegate_field: str, source_fields: set[str], field_prefix: str) -> None:
        """Initialize the inliner.

        Args:
            delegate_field: Name of the delegate field being removed
            source_fields: Set of field names from the source class
            field_prefix: Prefix for inlined fields
        """
        self.delegate_field = delegate_field
        self.source_fields = source_fields
        self.field_prefix = field_prefix
        # Map of temporary variable name -> base object expression
        # e.g., "tel" -> "person"
        self.temp_var_mappings: dict[str, cst.BaseExpression] = {}

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function and clean up statements that assign delegate field."""
        if not isinstance(original_node.body, cst.IndentedBlock):
            return updated_node

        # First pass: identify temp var assignments from original node
        temp_var_mappings: dict[str, cst.BaseExpression] = {}
        for stmt in original_node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for expr in stmt.body:
                    if isinstance(expr, cst.Assign) and len(expr.targets) == 1:
                        target = expr.targets[0].target
                        if isinstance(target, cst.Name) and isinstance(expr.value, cst.Attribute):
                            if expr.value.attr.value == self.delegate_field:
                                # Record the mapping: temp_var -> obj
                                temp_var_mappings[target.value] = expr.value.value

        if not temp_var_mappings:
            return updated_node

        # Second pass: transform the function body to:
        # 1. Replace uses of temp vars with the base object + inlined fields
        # 2. Remove the temp var assignments
        transformer = TempVarReplacer(
            temp_var_mappings, self.source_fields, self.field_prefix, self.delegate_field
        )
        return cast(cst.FunctionDef, updated_node.visit(transformer))


class TempVarReplacer(cst.CSTTransformer):
    """Replaces temporary variable uses and removes their assignments."""

    def __init__(
        self,
        temp_var_mappings: dict[str, cst.BaseExpression],
        source_fields: set[str],
        field_prefix: str,
        delegate_field: str,
    ) -> None:
        """Initialize the replacer.

        Args:
            temp_var_mappings: Map of temp var name to base object
            source_fields: Set of field names from the source class
            field_prefix: Prefix for inlined fields
            delegate_field: Name of the delegate field being removed
        """
        self.temp_var_mappings = temp_var_mappings
        self.source_fields = source_fields
        self.field_prefix = field_prefix
        self.delegate_field = delegate_field

    def leave_SimpleStatementLine(  # noqa: N802
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        """Remove statements that assign the delegate field to temp vars."""
        for expr in original_node.body:
            if isinstance(expr, cst.Assign) and len(expr.targets) == 1:
                target = expr.targets[0].target
                if isinstance(target, cst.Name) and isinstance(expr.value, cst.Attribute):
                    if expr.value.attr.value == self.delegate_field:
                        # Remove this statement
                        return cst.RemovalSentinel.REMOVE
        return updated_node

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Transform attribute accesses on temporary variables.

        Transforms: tel.area_code -> person.office_area_code
        """
        # Check if this is temp_var.field_name
        if isinstance(updated_node.value, cst.Name):
            temp_var_name = updated_node.value.value
            if temp_var_name in self.temp_var_mappings:
                field_name = updated_node.attr.value
                if field_name in self.source_fields:
                    # Replace temp_var.field_name with obj.prefix_field_name
                    base_obj = self.temp_var_mappings[temp_var_name]
                    inlined_field = self.field_prefix + field_name
                    return cst.Attribute(value=base_obj, attr=cst.Name(inlined_field))

        return updated_node


register_command(InlineClassCommand)
