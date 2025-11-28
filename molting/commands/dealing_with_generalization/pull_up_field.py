"""Pull Up Field refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    extract_init_field_assignments,
    find_method_in_class,
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

        # First pass: capture field info from source and target classes
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        capture_transformer = FieldCaptureTransformer(class_name, field_name, to_class)
        module.visit(capture_transformer)

        # Second pass: apply transformation with captured field info
        pull_up_transformer = PullUpFieldTransformer(
            class_name,
            field_name,
            to_class,
            capture_transformer.field_param_name,
            capture_transformer.parent_existing_params,
        )
        modified_tree = module.visit(pull_up_transformer)
        self.file_path.write_text(modified_tree.code)


class FieldCaptureTransformer(cst.CSTTransformer):
    """Visitor to capture field information from source and target classes."""

    def __init__(self, source_class: str, field_name: str, target_class: str) -> None:
        """Initialize the capture transformer.

        Args:
            source_class: Name of the class containing the field
            field_name: Name of the field to capture
            target_class: Name of the superclass
        """
        self.source_class = source_class
        self.field_name = field_name
        self.target_class = target_class
        self.field_param_name: str | None = None
        self.parent_existing_params: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Capture field information when visiting classes."""
        if node.name.value == self.source_class:
            init_method = find_method_in_class(node, "__init__")
            if init_method:
                # Extract field assignments to find the parameter
                field_assignments = extract_init_field_assignments(init_method)
                if self.field_name in field_assignments:
                    # The value should be a parameter reference
                    value = field_assignments[self.field_name]
                    if isinstance(value, cst.Name):
                        self.field_param_name = value.value
        elif node.name.value == self.target_class:
            # Capture existing parameters in parent __init__
            init_method = find_method_in_class(node, "__init__")
            if init_method and isinstance(init_method.params, cst.Parameters):
                for param in init_method.params.params:
                    if param.name.value != "self":
                        self.parent_existing_params.append(param.name.value)


class PullUpFieldTransformer(cst.CSTTransformer):
    """Transforms a module by pulling up a field from subclasses to superclass."""

    def __init__(
        self,
        source_class: str,
        field_name: str,
        target_class: str,
        field_param_name: str | None,
        parent_existing_params: list[str],
    ) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the subclass containing the field
            field_name: Name of the field to pull up
            target_class: Name of the superclass to pull the field to
            field_param_name: The parameter name for the field
            parent_existing_params: Existing parameters in parent __init__
        """
        self.source_class = source_class
        self.field_name = field_name
        self.target_class = target_class
        self.field_param_name = field_param_name or field_name
        self.parent_existing_params = parent_existing_params

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to pull up the field."""
        if original_node.name.value == self.target_class:
            # Add field to target class __init__
            return self._add_field_to_superclass(updated_node)
        elif original_node.name.value == self.source_class:
            # Update source subclass __init__ to use super() and remove field assignment
            return self._update_source_subclass(updated_node)
        elif self._is_subclass_of_target(original_node):
            # Update other subclasses __init__ to use super()
            return self._update_other_subclass(updated_node)
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
        # Check if superclass already has __init__
        init_method = find_method_in_class(class_node, "__init__")
        has_init = init_method is not None

        new_body_stmts: list[cst.BaseStatement] = []

        if not has_init:
            # Create new __init__ with existing params + field parameter
            all_params = self.parent_existing_params + [self.field_param_name]
            new_init = create_init_method(
                params=all_params,
                field_assignments=None,  # Will create self.param = param for each param
            )
            new_body_stmts.insert(0, new_init)
        else:
            # Superclass already has __init__, extend it by adding the new parameter
            for stmt in class_node.body.body:
                if stmt is not init_method:
                    new_body_stmts.append(cast(cst.BaseStatement, stmt))
                else:
                    # Extend existing __init__ with new parameter and assignment
                    new_init = self._extend_superclass_init(init_method)
                    new_body_stmts.append(new_init)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _extend_superclass_init(self, init_node: cst.FunctionDef) -> cst.FunctionDef:
        """Extend existing superclass __init__ with new parameter and assignment.

        Args:
            init_node: Existing __init__ method

        Returns:
            Modified __init__ method with added field parameter and assignment
        """
        # Add the field parameter to the parameter list
        new_params: list[cst.Param] = list(init_node.params.params)
        new_params.append(cst.Param(name=cst.Name(self.field_param_name)))

        # Add the field assignment to the body
        new_body_stmts: list[cst.BaseStatement] = list(init_node.body.body)
        field_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(self.field_name),
                            )
                        )
                    ],
                    value=cst.Name(self.field_param_name),
                )
            ]
        )
        new_body_stmts.append(field_assignment)

        # Create new __init__ with updated parameters and body
        return init_node.with_changes(
            params=init_node.params.with_changes(params=tuple(new_params)),
            body=init_node.body.with_changes(body=tuple(new_body_stmts)),
        )

    def _update_source_subclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Update source subclass to use super().__init__().

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

        # Extract parameters from current __init__
        params = []
        if isinstance(init_method.params, cst.Parameters):
            for param in init_method.params.params:
                if param.name.value != "self":
                    params.append(param.name.value)

        # Build super() arguments: existing parent params in order, then the field parameter
        super_args = []
        for param in self.parent_existing_params:
            if param in params:
                super_args.append(cst.Arg(value=cst.Name(param)))
        # Add the field parameter
        super_args.append(cst.Arg(value=cst.Name(self.field_param_name)))

        # Remove the field assignment from the field_assignments dict
        remaining_assignments = {k: v for k, v in field_assignments.items() if k != self.field_name}

        # Create new __init__ with super() call but keep other field assignments
        new_init = create_init_method(
            params=params,
            field_assignments=remaining_assignments,
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

    def _update_other_subclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Update other subclasses to use super().__init__().

        Args:
            class_node: The subclass definition to modify

        Returns:
            Modified class definition
        """
        init_method = find_method_in_class(class_node, "__init__")
        if not init_method:
            return class_node

        # Extract field assignments
        field_assignments = extract_init_field_assignments(init_method)
        if self.field_name not in field_assignments:
            return class_node

        # Extract parameters from current __init__
        params = []
        if isinstance(init_method.params, cst.Parameters):
            for param in init_method.params.params:
                if param.name.value != "self":
                    params.append(param.name.value)

        # Build super() arguments: existing parent params in order, then the field parameter
        super_args = []
        for param in self.parent_existing_params:
            if param in params:
                super_args.append(cst.Arg(value=cst.Name(param)))
        # Add the field parameter
        super_args.append(cst.Arg(value=cst.Name(self.field_param_name)))

        # Remove the field assignment
        remaining_assignments = {k: v for k, v in field_assignments.items() if k != self.field_name}

        # Create new __init__
        new_init = create_init_method(
            params=params,
            field_assignments=remaining_assignments,
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
