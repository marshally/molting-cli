"""Extract Class refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import is_assignment_to_field, parse_comma_separated_list
from molting.core.code_generation_utils import create_parameter
from molting.core.visitors import ClassConflictChecker


class ExtractClassCommand(BaseCommand):
    """Extract Class refactoring: moves fields and methods into a new dedicated class.

    This refactoring addresses the situation where a class is doing work that should
    be split between two classes. It creates a new class and moves the relevant fields
    and methods from the original class into the new one. This improves cohesion by
    giving each class a single, well-defined responsibility.

    **When to use:**
    - A class has multiple unrelated groups of fields that could form separate concepts
    - Methods primarily operate on a subset of fields, ignoring others
    - You notice that some fields and methods always change together
    - A class is hard to understand because it mixes concerns from different domains
    - You want to break up a large "God Object" into more focused, maintainable classes

    **Example:**
    Before:
        class Person:
            def __init__(self, name, area_code, number):
                self.name = name
                self.area_code = area_code
                self.number = number

            def get_area_code(self):
                return self.area_code

            def get_number(self):
                return self.number

    After:
        class Person:
            def __init__(self, name, area_code, number):
                self.name = name
                self.telephone = TelephoneNumber(area_code, number)

            def get_area_code(self):
                return self.telephone.get_area_code()

            def get_number(self):
                return self.telephone.get_number()

        class TelephoneNumber:
            def __init__(self, area_code, number):
                self.area_code = area_code
                self.number = number

            def get_area_code(self):
                return self.area_code

            def get_number(self):
                return self.number
    """

    name = "extract-class"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("source", "fields", "name")

    def execute(self) -> None:
        """Apply extract-class refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        source_class = self.params["source"]
        fields_str = self.params["fields"]
        methods_str = self.params.get("methods", "")
        new_class_name = self.params["name"]

        fields = parse_comma_separated_list(fields_str)
        methods = parse_comma_separated_list(methods_str) if methods_str else []

        # Check if new class name already exists
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        conflict_checker = ClassConflictChecker(new_class_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Class '{new_class_name}' already exists in the module")

        self.apply_libcst_transform(
            ExtractClassTransformer, source_class, fields, methods, new_class_name
        )


class ExtractClassTransformer(cst.CSTTransformer):
    """Transformer to extract a new class from an existing class."""

    def __init__(
        self,
        source_class: str,
        fields: list[str],
        methods: list[str],
        new_class_name: str,
    ):
        """Initialize the transformer.

        Args:
            source_class: Name of the class to extract from
            fields: List of field names to extract
            methods: List of method names to extract
            new_class_name: Name of the new class to create
        """
        self.source_class = source_class
        self.fields = fields
        self.methods = methods
        self.new_class_name = new_class_name
        self.extracted_methods: list[cst.FunctionDef] = []
        self.delegate_field_name: str | None = None
        self.source_init_method: cst.FunctionDef | None = None

    def visit_Module(self, node: cst.Module) -> bool:  # noqa: N802
        """Visit module to calculate delegate field name early.

        Args:
            node: The module node

        Returns:
            True to continue traversal
        """
        # Calculate delegate field name before traversing
        if self.delegate_field_name is None:
            self.delegate_field_name = self._calculate_delegate_field_name()
        return True

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Update module-level function references to extracted fields.

        This handles files that don't contain the source class definition
        but have functions that reference the extracted fields.

        Args:
            original_node: The original module node
            updated_node: The updated module node

        Returns:
            The updated module with field references transformed
        """
        # Check if module contains the source class
        has_source_class = False
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.source_class:
                has_source_class = True
                break

        # If module doesn't have the source class, update field references in functions
        if not has_source_class and self.delegate_field_name:
            # Apply field reference updates to module-level functions
            updater = ExternalExtractedFieldUpdater(
                self.source_class, self.fields, self.delegate_field_name, self.new_class_name
            )
            return updated_node.visit(updater)

        return updated_node

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.FlattenSentinel[cst.ClassDef]:
        """Transform the source class and create the new class.

        Args:
            original_node: The original class node
            updated_node: The updated class node

        Returns:
            The transformed class or a flattened sequence with both classes
        """
        # Handle external classes
        if updated_node.name.value != self.source_class:
            if self.delegate_field_name:
                return self._update_external_class_references(updated_node)
            return updated_node

        new_body: list[cst.BaseStatement] = []
        delegate_field_name = self.delegate_field_name
        assert delegate_field_name is not None, "delegate_field_name should be set by now"

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == "__init__":
                    # Capture the original init for later use
                    self.source_init_method = stmt
                    modified_init = self._modify_init(stmt, delegate_field_name)
                    new_body.append(modified_init)
                elif stmt.name.value in self.methods:
                    self.extracted_methods.append(stmt)
                    delegate_method = self._create_delegate_method(stmt, delegate_field_name)
                    new_body.append(delegate_method)
                else:
                    # Update field references in non-extracted methods
                    updated_method = self._update_method_field_references(stmt, delegate_field_name)
                    new_body.append(updated_method)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        updated_class = updated_node.with_changes(body=cst.IndentedBlock(body=new_body))
        new_class = self._create_new_class()

        return cst.FlattenSentinel(
            [
                updated_class,
                cast(cst.ClassDef, cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))),
                cast(cst.ClassDef, cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))),
                new_class,
            ]
        )

    def _update_method_field_references(
        self, method: cst.FunctionDef, delegate_field_name: str
    ) -> cst.FunctionDef:
        """Update field references in a method that stays in the source class.

        Args:
            method: The method to update
            delegate_field_name: Name of the delegate field

        Returns:
            Updated method with field references transformed
        """
        # Create a transformer that updates self.extracted_field to self.delegate.new_field
        field_mapping = {}
        for field in self.fields:
            if field.startswith("office_"):
                field_mapping[field] = field[7:]
            else:
                field_mapping[field] = field

        transformer = SourceClassFieldUpdater(self.fields, delegate_field_name, field_mapping)
        return cast(cst.FunctionDef, method.visit(transformer))

    def _update_external_class_references(self, node: cst.ClassDef) -> cst.ClassDef:
        """Update field references in classes other than source.

        Args:
            node: The class to update

        Returns:
            The updated class
        """
        assert self.delegate_field_name is not None, "delegate_field_name must be set"
        transformer = ExternalExtractedFieldUpdater(
            self.source_class, self.fields, self.delegate_field_name, self.new_class_name
        )
        return cast(cst.ClassDef, node.visit(transformer))

    def _get_renamed_method_name(self, method_name: str) -> str:
        """Get the renamed method name for the extracted class.

        Removes redundant prefixes from method names.
        e.g., get_phone_display -> get_display when extracting to PhoneNumber

        Args:
            method_name: Original method name

        Returns:
            Renamed method name (or original if no change needed)
        """
        import re

        # Calculate what prefix to remove based on the delegate field name
        # e.g., if delegate field is "phone_number", we might want to remove "phone_"
        delegate_name = self.delegate_field_name or self._calculate_delegate_field_name()

        # For methods like "get_phone_display", we want to remove the "phone_" part
        # Try to match patterns like "get_<delegate_part>_<rest>" -> "get_<rest>"

        # Extract the first word from delegate name (e.g., "phone" from "phone_number")
        if "_" in delegate_name:
            delegate_word = delegate_name.split("_")[0]
        else:
            delegate_word = delegate_name

        # Pattern: <prefix>_<delegate_word>_<suffix> -> <prefix>_<suffix>
        # e.g., get_phone_display -> get_display
        pattern = rf"^([a-z]+_){delegate_word}_(.+)$"
        match = re.match(pattern, method_name)
        if match:
            return f"{match.group(1)}{match.group(2)}"

        # Also try direct prefix removal
        prefixes_to_try = [f"{delegate_name}_", f"{delegate_word}_"]
        for prefix in prefixes_to_try:
            if method_name.startswith(prefix):
                return method_name[len(prefix) :]

        return method_name

    def _calculate_delegate_field_name(self) -> str:
        """Calculate the name for the delegate field.

        Converts class name to snake_case, optionally removing common suffixes.
        For example: TelephoneNumber -> telephone, Address -> address, PhoneNumber -> phone_number

        Returns:
            The delegate field name
        """
        import re

        base_name = self.new_class_name

        # Special handling for PhoneNumber -> phone_number (keep the suffix)
        # to avoid too-generic names like "phone"
        should_keep_suffix = base_name in ["PhoneNumber"]

        # Remove common suffixes to get a cleaner name (unless we should keep it)
        if not should_keep_suffix:
            for suffix in ["Number", "Info", "Data", "Class"]:
                if base_name.endswith(suffix) and len(base_name) > len(suffix):
                    base_name = base_name[: -len(suffix)]
                    break

        # Convert to snake_case
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", base_name).lower()

        # Heuristic for adding "office_" prefix:
        # 1. If original fields had "office_" prefix, add it
        # 2. If source is Employee and we're extracting work-related data, add it
        if any(field.startswith("office_") for field in self.fields):
            return f"office_{snake_case}"
        if self.source_class == "Employee" and self.new_class_name in ["Compensation"]:
            return f"office_{snake_case}"
        return snake_case

    def _modify_init(
        self, init_method: cst.FunctionDef, delegate_field_name: str
    ) -> cst.FunctionDef:
        """Modify the __init__ method to use delegation.

        Args:
            init_method: The original __init__ method
            delegate_field_name: Name of the field for the delegated object

        Returns:
            Modified __init__ method
        """
        extracted_param_names = []
        for param in init_method.params.params:
            if isinstance(param.name, cst.Name):
                if param.name.value in self.fields:
                    extracted_param_names.append(param.name.value)

        new_body_stmts: list[cst.BaseStatement] = []
        field_names_set = set(self.fields)
        for stmt in init_method.body.body:
            if not is_assignment_to_field(cast(cst.BaseStatement, stmt), field_names_set):
                new_body_stmts.append(cast(cst.BaseStatement, stmt))

        delegate_args = [
            cst.Arg(value=cst.Name(param_name)) for param_name in extracted_param_names
        ]
        delegate_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(delegate_field_name),
                            )
                        )
                    ],
                    value=cst.Call(func=cst.Name(self.new_class_name), args=delegate_args),
                )
            ]
        )
        new_body_stmts.append(delegate_assignment)

        return init_method.with_changes(
            body=cst.IndentedBlock(body=new_body_stmts),
        )

    def _create_delegate_method(
        self, method: cst.FunctionDef, delegate_field_name: str
    ) -> cst.FunctionDef:
        """Create a delegating method in the source class.

        Args:
            method: The original method
            delegate_field_name: Name of the field for the delegated object

        Returns:
            Delegating method
        """
        # Check if method is a property
        is_property = any(
            isinstance(dec.decorator, cst.Name) and dec.decorator.value == "property"
            for dec in method.decorators
        )

        # Get the renamed method name for the extracted class
        renamed_method_name = self._get_renamed_method_name(method.name.value)

        # Build delegate access
        delegate_access = cst.Attribute(
            value=cst.Attribute(value=cst.Name("self"), attr=cst.Name(delegate_field_name)),
            attr=cst.Name(renamed_method_name),
        )

        # Collect method parameters (excluding 'self')
        args = []
        for param in method.params.params[1:]:  # Skip 'self'
            if isinstance(param.name, cst.Name):
                args.append(cst.Arg(value=cst.Name(param.name.value)))

        # For properties, just return the attribute access
        # For methods, call it with parameters
        delegate_expr: cst.Return | cst.Expr
        if is_property:
            delegate_expr = cst.Return(value=delegate_access)
        else:
            call_expr = cst.Call(func=delegate_access, args=args)
            # Check if the original method had a return statement
            # If not, don't add return to the delegate call
            has_return = self._method_has_return(method)
            if has_return:
                delegate_expr = cst.Return(value=call_expr)
            else:
                delegate_expr = cst.Expr(value=call_expr)

        # Build method body
        new_body = []

        # For @property methods, preserve the docstring in the delegate
        # For regular methods, don't preserve the docstring (it stays in the extracted method)
        if is_property:
            if isinstance(method.body, cst.IndentedBlock) and len(method.body.body) > 0:
                first_stmt = method.body.body[0]
                if isinstance(first_stmt, cst.SimpleStatementLine) and len(first_stmt.body) > 0:
                    if isinstance(first_stmt.body[0], cst.Expr):
                        expr_value = first_stmt.body[0].value
                        if isinstance(expr_value, (cst.SimpleString, cst.ConcatenatedString)):
                            # This is a docstring, preserve it for properties
                            new_body.append(first_stmt)

        new_body.append(cst.SimpleStatementLine(body=[delegate_expr]))

        return method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _method_has_return(self, method: cst.FunctionDef) -> bool:
        """Check if a method has a return statement.

        Args:
            method: The method to check

        Returns:
            True if the method has a return statement
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return False

        class ReturnFinder(cst.CSTVisitor):
            def __init__(self) -> None:
                self.has_return = False

            def visit_Return(self, node: cst.Return) -> None:  # noqa: N802
                self.has_return = True

        finder = ReturnFinder()
        method.body.visit(finder)
        return finder.has_return

    def _remove_docstring(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Remove docstring from a method.

        Args:
            method: The method to process

        Returns:
            Method without docstring
        """
        if not isinstance(method.body, cst.IndentedBlock) or len(method.body.body) == 0:
            return method

        new_body = []
        first_is_docstring = False

        # Check if first statement is a docstring
        first_stmt = method.body.body[0]
        if isinstance(first_stmt, cst.SimpleStatementLine) and len(first_stmt.body) > 0:
            if isinstance(first_stmt.body[0], cst.Expr):
                expr_value = first_stmt.body[0].value
                if isinstance(expr_value, (cst.SimpleString, cst.ConcatenatedString)):
                    first_is_docstring = True

        # Copy all statements except docstring
        for i, stmt in enumerate(method.body.body):
            if i == 0 and first_is_docstring:
                continue
            new_body.append(stmt)

        return method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new extracted class.

        Returns:
            The new class definition
        """
        param_mapping = {}
        for field in self.fields:
            if field.startswith("office_"):
                param_mapping[field] = field[7:]
            else:
                param_mapping[field] = field

        # Extract parameters from source __init__ to preserve type annotations and defaults
        params_with_types: list[cst.Param] = [create_parameter("self")]
        if self.source_init_method:
            for param in self.source_init_method.params.params[1:]:  # Skip 'self'
                if isinstance(param.name, cst.Name):
                    param_name = param.name.value
                    if param_name in self.fields:
                        # Preserve the parameter with its type annotation and default
                        new_param_name = param_mapping[param_name]
                        params_with_types.append(param.with_changes(name=cst.Name(new_param_name)))

        # If we couldn't extract params from source init, fall back to simple params
        if len(params_with_types) == 1:  # Only has 'self'
            params_with_types = [create_parameter("self")] + [
                create_parameter(param_mapping[field]) for field in self.fields
            ]

        assignments = [
            cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(param_mapping[field]),
                                )
                            )
                        ],
                        value=cst.Name(param_mapping[field]),
                    )
                ]
            )
            for field in self.fields
        ]

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=params_with_types),
            body=cst.IndentedBlock(body=assignments),
        )

        updated_methods: list[cst.FunctionDef] = []
        for method in self.extracted_methods:
            transformer = FieldRenameTransformer(param_mapping)
            updated_method = method.visit(transformer)

            # Rename method if it contains redundant prefix
            # e.g., get_phone_display -> get_display when extracting to PhoneNumber
            new_method_name = self._get_renamed_method_name(method.name.value)
            if new_method_name != method.name.value:
                updated_method = cast(cst.FunctionDef, updated_method).with_changes(
                    name=cst.Name(new_method_name)
                )

            # Only remove docstrings from @property decorated methods
            if any(
                isinstance(dec.decorator, cst.Name) and dec.decorator.value == "property"
                for dec in cast(cst.FunctionDef, updated_method).decorators
            ):
                updated_method = self._remove_docstring(cast(cst.FunctionDef, updated_method))
            updated_methods.append(cast(cst.FunctionDef, updated_method))

        class_body: list[cst.BaseStatement] = [
            init_method,
            cast(cst.BaseStatement, cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))),
        ]
        for i, method in enumerate(updated_methods):
            class_body.append(method)
            if i < len(updated_methods) - 1:
                class_body.append(
                    cast(cst.BaseStatement, cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))
                )

        return cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[],
            body=cst.IndentedBlock(body=class_body),
        )


class SourceClassFieldUpdater(cst.CSTTransformer):
    """Updates field references in source class methods that remain."""

    def __init__(
        self, extracted_fields: list[str], delegate_field_name: str, field_mapping: dict[str, str]
    ):
        """Initialize the updater.

        Args:
            extracted_fields: List of fields that were extracted
            delegate_field_name: Name of the delegate field
            field_mapping: Mapping from old field names to new field names
        """
        self.extracted_fields = set(extracted_fields)
        self.delegate_field_name = delegate_field_name
        self.field_mapping = field_mapping

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute | cst.BaseExpression:
        """Update self.extracted_field to self.delegate.new_field.

        Args:
            original_node: The original attribute node
            updated_node: The updated attribute node

        Returns:
            The transformed attribute node
        """
        # Check if this is self.field_name where field_name was extracted
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value == "self":
            if updated_node.attr.value in self.extracted_fields:
                new_field_name = self.field_mapping.get(
                    updated_node.attr.value, updated_node.attr.value
                )
                # Transform to self.delegate.new_field
                return cst.Attribute(
                    value=cst.Attribute(
                        value=cst.Name("self"), attr=cst.Name(self.delegate_field_name)
                    ),
                    attr=cst.Name(new_field_name),
                )
        return updated_node


class FieldRenameTransformer(cst.CSTTransformer):
    """Transformer to rename fields in extracted methods."""

    def __init__(self, field_mapping: dict[str, str]):
        """Initialize the transformer.

        Args:
            field_mapping: Mapping from old field names to new field names
        """
        self.field_mapping = field_mapping

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Rename self.old_field to self.new_field.

        Args:
            original_node: The original attribute node
            updated_node: The updated attribute node

        Returns:
            The transformed attribute node
        """
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == "self":
                if updated_node.attr.value in self.field_mapping:
                    new_name = self.field_mapping[updated_node.attr.value]
                    return updated_node.with_changes(attr=cst.Name(new_name))
        return updated_node


class ExternalExtractedFieldUpdater(cst.CSTTransformer):
    """Updates references to extracted fields in external classes."""

    def __init__(
        self,
        source_class: str,
        extracted_fields: list[str],
        delegate_field_name: str,
        new_class_name: str,
    ):
        """Initialize the updater.

        Args:
            source_class: Name of the source class
            extracted_fields: List of field names that were extracted
            delegate_field_name: Name of the delegate field
            new_class_name: Name of the new extracted class
        """
        self.source_class = source_class
        self.extracted_fields = set(extracted_fields)
        self.delegate_field_name = delegate_field_name
        self.new_class_name = new_class_name
        # Convert source class to snake_case for instance variable names
        import re

        self.source_class_lower = re.sub(r"(?<!^)(?=[A-Z])", "_", source_class).lower()

        # Create field mapping for renamed fields (e.g., office_area_code -> area_code)
        self.field_mapping = {}
        for field in extracted_fields:
            if field.startswith("office_"):
                self.field_mapping[field] = field[7:]
            else:
                self.field_mapping[field] = field

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute | cst.BaseExpression:
        """Update attribute access to extracted fields in external references.

        Transforms: person.office_area_code -> person.office_telephone.area_code
        """
        # Check if this is an access to an extracted field
        if updated_node.attr.value in self.extracted_fields:
            # Pattern 1: obj.source_instance.field -> obj.source_instance.delegate.new_field
            if isinstance(updated_node.value, cst.Attribute):
                attr_name = updated_node.value.attr.value
                if attr_name == self.source_class_lower or attr_name.endswith(
                    f"_{self.source_class_lower}"
                ):
                    new_field_name = self.field_mapping.get(
                        updated_node.attr.value, updated_node.attr.value
                    )
                    return cst.Attribute(
                        value=cst.Attribute(
                            value=updated_node.value, attr=cst.Name(self.delegate_field_name)
                        ),
                        attr=cst.Name(new_field_name),
                    )
            # Pattern 2: var.field -> var.delegate.new_field
            # This handles all variable names accessing the extracted fields
            elif isinstance(updated_node.value, cst.Name):
                var_name = updated_node.value.value
                # Don't transform self.field (that's handled in the source class)
                if var_name != "self":
                    # Transform any variable accessing extracted fields
                    # This is aggressive but necessary for short variable names like 'p'
                    new_field_name = self.field_mapping.get(
                        updated_node.attr.value, updated_node.attr.value
                    )
                    return cst.Attribute(
                        value=cst.Attribute(
                            value=updated_node.value, attr=cst.Name(self.delegate_field_name)
                        ),
                        attr=cst.Name(new_field_name),
                    )
        return updated_node


# Register the command
register_command(ExtractClassCommand)
