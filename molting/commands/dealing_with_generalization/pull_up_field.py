"""Pull Up Field refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    find_method_in_class,
    is_pass_statement,
    is_self_field_assignment,
    parse_target,
)
from molting.core.code_generation_utils import (
    create_field_assignment,
    create_super_init_call,
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
        self.field_param: cst.Param | None = None
        self.field_value: cst.BaseExpression | None = None

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to pull up the field."""
        if original_node.name.value == self.target_class:
            # Add field to target class __init__
            return self._add_field_to_superclass(updated_node)
        elif original_node.name.value == self.source_class:
            # Capture field info from source class before modifying
            self._capture_field_info(original_node)
            # Modify source class to call super().__init__(field)
            return self._modify_subclass(updated_node)
        elif self._is_sibling_class(original_node):
            # Modify sibling subclasses
            return self._modify_subclass(updated_node)
        return updated_node

    def _is_sibling_class(self, class_node: cst.ClassDef) -> bool:
        """Check if class is a sibling subclass (inherits from target_class).

        Args:
            class_node: Class definition to check

        Returns:
            True if class inherits from target_class
        """
        if not class_node.bases:
            return False

        for base in class_node.bases:
            if isinstance(base.value, cst.Name) and base.value.value == self.target_class:
                return True
        return False

    def _capture_field_info(self, class_node: cst.ClassDef) -> None:
        """Capture field parameter and value from source class __init__.

        Args:
            class_node: The source class definition
        """
        init_method = find_method_in_class(class_node, "__init__")
        if not init_method or not isinstance(init_method.body, cst.IndentedBlock):
            return

        # Capture parameter from __init__ signature
        for param in init_method.params.params:
            if param.name.value != "self":
                self.field_param = param
                break

        # Capture field assignment value
        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                if is_self_field_assignment(stmt, {self.field_name}):
                    self.field_value = self._extract_assignment_value(stmt)
                    break

    def _extract_assignment_value(self, stmt: cst.SimpleStatementLine) -> cst.BaseExpression | None:
        """Extract the value from a field assignment statement.

        Args:
            stmt: Statement containing field assignment

        Returns:
            The assigned value, or None if not found
        """
        for body_stmt in stmt.body:
            if isinstance(body_stmt, cst.Assign):
                return body_stmt.value
        return None

    def _add_field_to_superclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add field to superclass __init__.

        Args:
            class_node: The superclass definition to modify

        Returns:
            Modified class definition
        """
        # Check if class already has __init__
        init_method = find_method_in_class(class_node, "__init__")

        new_body_stmts: list[cst.BaseStatement] = []

        if init_method:
            # Add field to existing __init__
            modified_init = self._add_field_to_init(init_method)
            for stmt in class_node.body.body:
                stmt = cast(cst.BaseStatement, stmt)
                if stmt is init_method:
                    new_body_stmts.append(modified_init)
                else:
                    new_body_stmts.append(stmt)
        else:
            # Create new __init__ with field
            new_init = self._create_init_with_field()
            # Remove pass statements and add new __init__
            for stmt in class_node.body.body:
                stmt = cast(cst.BaseStatement, stmt)
                if not is_pass_statement(stmt):
                    new_body_stmts.append(stmt)
            new_body_stmts.insert(0, new_init)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _create_init_with_field(self) -> cst.FunctionDef:
        """Create new __init__ method with field assignment.

        Returns:
            New __init__ method
        """
        # Use captured parameter or create default
        param = self.field_param if self.field_param else cst.Param(name=cst.Name(self.field_name))

        field_value = self.field_value if self.field_value else cst.Name(self.field_name)
        field_assignment = create_field_assignment(self.field_name, field_value)

        return cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self")), param]),
            body=cst.IndentedBlock(body=[field_assignment]),
        )

    def _add_field_to_init(self, init_node: cst.FunctionDef) -> cst.FunctionDef:
        """Add field parameter and assignment to existing __init__ method.

        Args:
            init_node: Existing __init__ method

        Returns:
            Modified __init__ method
        """
        # Add parameter to __init__ signature
        param = self.field_param if self.field_param else cst.Param(name=cst.Name(self.field_name))
        new_params = list(init_node.params.params) + [param]
        new_params_obj = init_node.params.with_changes(params=new_params)

        # Add field assignment to body
        if isinstance(init_node.body, cst.IndentedBlock):
            field_value = self.field_value if self.field_value else cst.Name(self.field_name)
            field_assignment = create_field_assignment(self.field_name, field_value)
            new_stmts = list(init_node.body.body) + [field_assignment]
            new_body = cst.IndentedBlock(body=new_stmts)
        else:
            new_body = init_node.body

        return init_node.with_changes(params=new_params_obj, body=new_body)

    def _modify_subclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Modify subclass to call super().__init__(field) instead of setting field directly.

        Args:
            class_node: The subclass definition to modify

        Returns:
            Modified class definition
        """
        init_method = find_method_in_class(class_node, "__init__")
        if not init_method or not isinstance(init_method.body, cst.IndentedBlock):
            return class_node

        # Modify __init__ to replace field assignment with super().__init__(value)
        new_body_stmts: list[cst.BaseStatement] = []
        found_field_assignment = False

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                if is_self_field_assignment(stmt, {self.field_name}):
                    # Replace with super().__init__(value)
                    field_value = None
                    for body_stmt in stmt.body:
                        if isinstance(body_stmt, cst.Assign):
                            field_value = body_stmt.value
                            break

                    if field_value:
                        super_call = create_super_init_call([cst.Arg(value=field_value)])
                        new_body_stmts.append(super_call)
                        found_field_assignment = True
                else:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        if not found_field_assignment:
            return class_node

        modified_init = init_method.with_changes(body=cst.IndentedBlock(body=new_body_stmts))

        # Replace init method in class body
        new_class_body: list[cst.BaseStatement] = []
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if stmt is init_method:
                new_class_body.append(modified_init)
            else:
                new_class_body.append(stmt)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_class_body))
        )


# Register the command
register_command(PullUpFieldCommand)
