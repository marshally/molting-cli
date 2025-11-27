"""Pull Up Constructor Body refactoring command."""

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


class PullUpConstructorBodyCommand(BaseCommand):
    """Command to pull up constructor body from subclass to superclass."""

    name = "pull-up-constructor-body"

    def validate(self) -> None:
        """Validate that required parameters are present and well-formed.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.validate_required_params("target", "to")

        # Validate target format (ClassName::__init__)
        try:
            class_name, method_name = parse_target(self.params["target"], expected_parts=2)
            if method_name != "__init__":
                raise ValueError("Target must be a constructor (__init__)")
        except ValueError as e:
            raise ValueError(f"Invalid target format for pull-up-constructor-body: {e}") from e

    def execute(self) -> None:
        """Apply pull-up-constructor-body refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        to_class = self.params["to"]

        # Parse target to get class and method names
        class_name, _ = parse_target(target, expected_parts=2)

        # First pass: capture the constructor to analyze common parameters
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        capture_transformer = ConstructorCaptureTransformer(class_name, to_class)
        module.visit(capture_transformer)
        capture_transformer.finalize()

        # Second pass: apply transformation
        move_transformer = PullUpConstructorBodyTransformer(
            class_name,
            to_class,
            capture_transformer.common_params,
            capture_transformer.common_assignments,
        )
        modified_tree = module.visit(move_transformer)
        self.file_path.write_text(modified_tree.code)


class ConstructorCaptureTransformer(cst.CSTVisitor):
    """Visitor to capture constructor information from all subclasses."""

    def __init__(self, source_class: str, target_class: str) -> None:
        """Initialize the capture transformer.

        Args:
            source_class: Name of the subclass containing the constructor
            target_class: Name of the superclass to pull constructor body to
        """
        self.source_class = source_class
        self.target_class = target_class
        self.common_params: list[str] = []
        self.common_assignments: dict[str, cst.BaseExpression] = {}
        self.all_subclass_assignments: list[dict[str, cst.BaseExpression]] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Capture constructor parameters from all subclasses of target."""
        # Check if this is a subclass of the target class
        if self._is_subclass_of_target(node):
            init_method = find_method_in_class(node, "__init__")
            if init_method:
                # Extract field assignments
                assignments = extract_init_field_assignments(init_method)
                self.all_subclass_assignments.append(assignments)

    def _is_subclass_of_target(self, class_node: cst.ClassDef) -> bool:
        """Check if class is a subclass of the target class."""
        if not class_node.bases:
            return False

        for base in class_node.bases:
            if isinstance(base.value, cst.Name) and base.value.value == self.target_class:
                return True

        return False

    def finalize(self) -> None:
        """After visiting all nodes, determine common parameters."""
        # Find parameters that exist in ALL subclasses
        if self.all_subclass_assignments:
            # Start with first subclass's assignments
            common_fields = set(self.all_subclass_assignments[0].keys())

            # Intersect with all other subclasses
            for assignments in self.all_subclass_assignments[1:]:
                common_fields &= set(assignments.keys())

            # Convert to list maintaining order from first subclass
            self.common_params = [
                field for field in self.all_subclass_assignments[0].keys() if field in common_fields
            ]

            # Store one example of assignments (from first subclass)
            self.common_assignments = {
                field: self.all_subclass_assignments[0][field] for field in self.common_params
            }


class PullUpConstructorBodyTransformer(cst.CSTTransformer):
    """Transforms a module by pulling up constructor body from subclass to superclass."""

    def __init__(
        self,
        source_class: str,
        target_class: str,
        common_params: list[str],
        common_assignments: dict[str, cst.BaseExpression],
    ) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the subclass containing the constructor
            target_class: Name of the superclass to pull constructor body to
            common_params: Common parameters to pull up (field names)
            common_assignments: Common field assignments to pull up
        """
        self.source_class = source_class
        self.target_class = target_class
        self.common_params = common_params  # These are field names that are common
        self.common_assignments = common_assignments

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to pull up the constructor body."""
        if original_node.name.value == self.target_class:
            # Add constructor to target class
            return self._add_constructor_to_superclass(updated_node)
        elif self._is_subclass_of_target(original_node):
            # Update subclass constructor to use super()
            return self._update_subclass_constructor(updated_node)
        return updated_node

    def _is_subclass_of_target(self, class_node: cst.ClassDef) -> bool:
        """Check if class is a subclass of the target class.

        Args:
            class_node: The class definition to check

        Returns:
            True if class inherits from target class
        """
        if not class_node.bases:
            return False

        for base in class_node.bases:
            if isinstance(base.value, cst.Name) and base.value.value == self.target_class:
                return True

        return False

    def _add_constructor_to_superclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add constructor to superclass.

        Args:
            class_node: The superclass definition to modify

        Returns:
            Modified class definition
        """
        # Check if superclass already has __init__
        init_method = find_method_in_class(class_node, "__init__")
        if init_method:
            # Superclass already has a constructor, don't modify
            return class_node

        new_body_stmts: list[cst.BaseStatement] = []

        # Remove pass statement if present
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if not is_pass_statement(stmt):
                new_body_stmts.append(stmt)

        # Create new __init__ with common parameters
        # common_params contains the field names, which match the parameter names
        new_init = create_init_method(
            params=self.common_params,
            field_assignments=None,  # Will create self.param = param for each
        )
        new_body_stmts.insert(0, new_init)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _update_subclass_constructor(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Update subclass constructor to use super().__init__().

        Args:
            class_node: The subclass definition to modify

        Returns:
            Modified class definition
        """
        init_method = find_method_in_class(class_node, "__init__")
        if not init_method:
            return class_node

        # Extract current parameters and field assignments
        current_params = []
        if isinstance(init_method.params, cst.Parameters):
            for param in init_method.params.params:
                if param.name.value != "self":
                    current_params.append(param.name.value)

        assignments = extract_init_field_assignments(init_method)

        # Determine which params should be passed to super()
        # common_params are field names - we pass the corresponding parameter values
        super_args = []
        for field_name in self.common_params:
            if field_name in assignments:
                # Use the value from the assignment
                super_args.append(cst.Arg(value=assignments[field_name]))

        # Determine remaining field assignments (those not pulled up)
        remaining_assignments = {
            field: value for field, value in assignments.items() if field not in self.common_params
        }

        # Create new __init__ with super() call
        new_init = create_init_method(
            params=current_params,
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
register_command(PullUpConstructorBodyCommand)
