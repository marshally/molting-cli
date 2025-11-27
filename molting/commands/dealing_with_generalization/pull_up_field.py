"""Pull Up Field refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    extract_init_field_assignments,
    find_method_in_class,
    is_pass_statement,
    parse_target,
)
from molting.core.code_generation_utils import (
    create_init_method,
)


class PullUpFieldCommand(BaseCommand):
    """Command to pull up a field from subclasses to superclass."""

    name = "pull-up-field"

    def validate(self) -> None:
        """Validate that required parameters are present and well-formed.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.validate_required_params("target", "to")

        # Validate target format (ClassName::field_name)
        try:
            parse_target(self.params["target"], expected_parts=2)
        except ValueError as e:
            raise ValueError(f"Invalid target format for pull-up-field: {e}") from e

    def execute(self) -> None:
        """Apply pull-up-field refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        to_class = self.params["to"]

        # Parse target to get class and field names
        class_name, field_name = parse_target(target, expected_parts=2)

        # Apply transformation
        self.apply_libcst_transform(PullUpFieldTransformer, class_name, field_name, to_class)


class PullUpFieldTransformer(cst.CSTTransformer):
    """Transforms a module by pulling up a field from subclasses to superclass."""

    def __init__(self, source_class: str, field_name: str, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the subclass containing the field
            field_name: Name of the field to pull up
            target_class: Name of the superclass to pull the field to
        """
        self.source_class = source_class
        self.field_name = field_name
        self.target_class = target_class
        self.field_params: list[str] = []

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to pull up the field."""
        if original_node.name.value == self.target_class:
            # Add field to target class __init__
            return self._add_field_to_superclass(updated_node)
        elif self._is_subclass_of_target(original_node):
            # Update subclass __init__ to use super()
            return self._update_subclass(updated_node)
        return updated_node

    def _is_subclass_of_target(self, class_node: cst.ClassDef) -> bool:
        """Check if class is a subclass of the target class.

        Args:
            class_node: The class definition to check

        Returns:
            True if class inherits from target class
        """
        # Check if class has any base classes
        if not class_node.bases:
            return False

        # Check if any base is the target class
        for base in class_node.bases:
            if isinstance(base.value, cst.Name) and base.value.value == self.target_class:
                return True

        return False

    def _add_field_to_superclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add field to superclass __init__.

        Args:
            class_node: The superclass definition to modify

        Returns:
            Modified class definition
        """
        # First pass: find __init__ in subclasses to extract field parameters
        if not self.field_params:
            # We need to extract parameter info from the first subclass we encounter
            # For now, we'll assume the parameter name matches the field name
            self.field_params = [self.field_name]

        # Check if superclass already has __init__
        init_method = find_method_in_class(class_node, "__init__")
        has_init = init_method is not None

        new_body_stmts: list[cst.BaseStatement] = []

        if not has_init:
            # Remove pass statement if present
            for stmt in class_node.body.body:
                stmt = cast(cst.BaseStatement, stmt)
                if not is_pass_statement(stmt):
                    new_body_stmts.append(stmt)

            # Create new __init__ with field
            new_init = create_init_method(
                params=self.field_params,
                field_assignments=None,  # Will create self.field_name = field_name
            )
            new_body_stmts.insert(0, new_init)
        else:
            # Superclass already has __init__, we should extend it
            # For simplicity, we'll replace it with a new one that includes the field
            for stmt in class_node.body.body:
                if stmt is not init_method:
                    new_body_stmts.append(cast(cst.BaseStatement, stmt))
                else:
                    # Create modified __init__
                    new_init = self._create_updated_superclass_init(init_method)
                    new_body_stmts.append(new_init)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _create_updated_superclass_init(self, init_node: cst.FunctionDef) -> cst.FunctionDef:
        """Create updated __init__ for superclass with the new field.

        Args:
            init_node: Existing __init__ method

        Returns:
            Modified __init__ method with field parameter and assignment
        """
        # Extract existing parameters (excluding self)
        existing_params = []
        if isinstance(init_node.params, cst.Parameters):
            for param in init_node.params.params:
                if param.name.value != "self":
                    existing_params.append(param.name.value)

        # Add the new field parameter
        all_params = existing_params + [self.field_name]

        # Create new __init__ with all parameters
        return create_init_method(params=all_params, field_assignments=None)

    def _update_subclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Update subclass to use super().__init__() instead of direct assignment.

        Args:
            class_node: The subclass definition to modify

        Returns:
            Modified class definition
        """
        init_method = find_method_in_class(class_node, "__init__")
        if not init_method:
            return class_node

        # Extract field assignments to find the parameter
        field_assignments = extract_init_field_assignments(init_method)
        if self.field_name not in field_assignments:
            return class_node

        # Get the parameter value for the field
        field_value = field_assignments[self.field_name]

        # Extract parameters from current __init__
        params = []
        if isinstance(init_method.params, cst.Parameters):
            for param in init_method.params.params:
                if param.name.value != "self":
                    params.append(param.name.value)

        # Create super().__init__() call with field parameter
        super_args = [cst.Arg(value=field_value)]

        # Create new __init__ with super() call and no field assignment
        new_init = create_init_method(
            params=params,
            field_assignments={},  # No direct field assignments
            super_call_args=super_args,
        )

        # Replace __init__ in class body
        new_body_stmts: list[cst.BaseStatement] = []
        for stmt in class_node.body.body:
            if stmt is init_method:
                new_body_stmts.append(new_init)
            else:
                new_body_stmts.append(cast(cst.BaseStatement, stmt))

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )


# Register the command
register_command(PullUpFieldCommand)
