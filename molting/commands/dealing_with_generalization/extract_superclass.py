"""Extract Superclass refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    extract_init_field_assignments,
    find_method_in_class,
    find_self_field_assignment,
    parse_comma_separated_list,
)
from molting.core.code_generation_utils import create_init_method


class ExtractSuperclassCommand(BaseCommand):
    """Extract common features from multiple classes into a new superclass.

    The Extract Superclass refactoring identifies duplicate code and behavior
    shared across two or more classes and consolidates them into a new parent
    class. This eliminates duplication and reveals common abstractions in your
    codebase, making it easier to maintain and extend.

    **When to use:**
    - Multiple classes share the same fields and methods
    - You want to reduce code duplication and improve maintainability
    - You're preparing to implement a common interface or protocol
    - You need to establish a shared abstraction for related classes

    **Example:**
    Before:
        class Cat:
            def __init__(self, name, age):
                self.name = name
                self.age = age

            def get_age(self):
                return self.age

        class Dog:
            def __init__(self, name, age):
                self.name = name
                self.age = age

            def get_age(self):
                return self.age

    After:
        class Animal:
            def __init__(self, name, age):
                self.name = name
                self.age = age

            def get_age(self):
                return self.age

        class Cat(Animal):
            pass

        class Dog(Animal):
            pass
    """

    name = "extract-superclass"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("targets", "name")

    def execute(self) -> None:
        """Apply extract-superclass refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        targets_str = self.params["targets"]
        superclass_name = self.params["name"]

        # Parse target classes
        target_classes = parse_comma_separated_list(targets_str)

        # Check for name conflicts - if the superclass name already exists, skip
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        for stmt in module.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == superclass_name:
                # Class with target name already exists, skip the refactoring
                return

        # Apply transformation
        self.apply_libcst_transform(ExtractSuperclassTransformer, target_classes, superclass_name)


class ExtractSuperclassTransformer(cst.CSTTransformer):
    """Transforms classes to extract a common superclass."""

    def __init__(self, target_classes: list[str], superclass_name: str) -> None:
        """Initialize the transformer.

        Args:
            target_classes: Names of the classes to extract from
            superclass_name: Name of the new superclass
        """
        self.target_classes = target_classes
        self.superclass_name = superclass_name
        self.class_defs: dict[str, cst.ClassDef] = {}
        self.common_fields: set[str] = set()
        self.common_methods: set[str] = set()

    def visit_Module(self, node: cst.Module) -> bool:  # noqa: N802
        """Visit module to find target classes and identify common features."""
        # First pass: collect class definitions
        for stmt in node.body:
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value in self.target_classes:
                    self.class_defs[stmt.name.value] = stmt

        # Identify common fields and methods
        if self.class_defs:
            self._find_common_features()

        return True

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and insert the superclass."""
        if not self.class_defs:
            return updated_node

        # Find the position to insert the superclass (before first target class)
        first_target_index = None
        new_body: list[cst.BaseStatement] = []

        for i, stmt in enumerate(updated_node.body):
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.target_classes[0]:
                    first_target_index = i
                    # Insert superclass before the first target class
                    superclass = self._create_superclass()
                    new_body.append(superclass)

            new_body.append(stmt)

        if first_target_index is None:
            return updated_node

        return updated_node.with_changes(body=tuple(new_body))

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and update to inherit from superclass."""
        if original_node.name.value not in self.target_classes:
            return updated_node

        # Add inheritance from superclass
        new_bases = list(updated_node.bases) + [cst.Arg(value=cst.Name(self.superclass_name))]

        # Update class body to remove common features and add super().__init__()
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            # Skip common methods
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == "__init__":
                    # Transform __init__ to call super()
                    stmt = self._transform_init_method(stmt)
                    new_body_stmts.append(stmt)
                elif stmt.name.value not in self.common_methods:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        return updated_node.with_changes(
            bases=new_bases, body=updated_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _find_common_features(self) -> None:
        """Identify common fields and methods across target classes."""
        all_fields = []
        all_methods = []

        for class_def in self.class_defs.values():
            class_fields, class_methods = self._extract_class_features(class_def)
            all_fields.append(set(class_fields))
            all_methods.append(set(class_methods))

        # Find common features
        if all_fields:
            self.common_fields = set.intersection(*all_fields)
        if all_methods:
            self.common_methods = set.intersection(*all_methods)

        # Remove __init__ from common methods since we handle it separately
        self.common_methods.discard("__init__")

    def _extract_class_features(self, class_def: cst.ClassDef) -> tuple[list[str], list[str]]:
        """Extract field and method names from a class.

        Args:
            class_def: The class definition

        Returns:
            Tuple of (fields, methods)
        """
        fields: list[str] = []
        methods: list[str] = []

        # Look for __init__ method to find fields
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                methods.append(stmt.name.value)
                if stmt.name.value == "__init__":
                    # Extract fields from __init__
                    field_assignments = extract_init_field_assignments(stmt)
                    fields.extend(field_assignments.keys())

        return fields, methods

    def _create_superclass(self) -> cst.ClassDef:
        """Create the superclass with common features.

        Returns:
            The new superclass definition
        """
        # Create __init__ method with common fields
        init_method = create_init_method(
            params=sorted(self.common_fields) if self.common_fields else []
        )

        # Create common methods
        methods: list[cst.BaseStatement] = [init_method]

        # Add all common methods (except __init__ which we already added)
        for method_name in sorted(self.common_methods):
            method = self._find_method_in_classes(method_name)
            if method:
                methods.append(method)

        # Create the superclass
        superclass = cst.ClassDef(
            name=cst.Name(self.superclass_name),
            body=cst.IndentedBlock(body=methods),
        )

        return superclass

    def _find_method_in_classes(self, method_name: str) -> cst.FunctionDef | None:
        """Find a method by name in any of the target classes.

        Args:
            method_name: Name of the method to find

        Returns:
            The method definition if found, None otherwise
        """
        for class_def in self.class_defs.values():
            method = find_method_in_class(class_def, method_name)
            if method:
                return method
        return None

    def _transform_init_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform the __init__ method to call super().__init__() and handle common fields.

        Args:
            node: The __init__ method to transform

        Returns:
            The transformed __init__ method
        """
        # Create super().__init__() call with common fields
        call_args = []
        for field in sorted(self.common_fields):
            call_args.append(cst.Arg(value=cst.Name(field)))

        super_call = cst.Expr(
            value=cst.Call(
                func=cst.Attribute(
                    value=cst.Call(func=cst.Name("super")), attr=cst.Name("__init__")
                ),
                args=call_args,
            )
        )

        super_call_stmt = cst.SimpleStatementLine(body=[super_call])

        # Collect non-common field assignments from original __init__
        new_stmts: list[cst.BaseStatement] = [super_call_stmt]

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                # Keep non-common field assignments and other statements
                if isinstance(stmt, cst.SimpleStatementLine):
                    result = find_self_field_assignment(stmt)
                    if result:
                        field_name, _ = result
                        # Keep only non-common field assignments
                        if field_name not in self.common_fields:
                            new_stmts.append(stmt)
                    else:
                        # Not a self.field assignment, keep it
                        new_stmts.append(stmt)
                else:
                    new_stmts.append(stmt)

        # Ensure we have at least one statement
        if len(new_stmts) == 1:
            new_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return node.with_changes(body=cst.IndentedBlock(body=new_stmts))


# Register the command
register_command(ExtractSuperclassCommand)
