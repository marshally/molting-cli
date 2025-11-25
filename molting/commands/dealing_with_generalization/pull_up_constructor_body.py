"""Pull Up Constructor Body refactoring command."""

from typing import Any, cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_class, is_pass_statement, parse_target
from molting.core.code_generation_utils import create_field_assignment, create_super_init_call


class PullUpConstructorBodyCommand(BaseCommand):
    """Command to pull up common constructor body from subclasses to superclass."""

    name = "pull-up-constructor-body"

    def validate(self) -> None:
        """Validate that required parameters are present and well-formed.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        self.validate_required_params("target", "to")

        # Validate target format (ClassName::__init__)
        try:
            parse_target(self.params["target"], expected_parts=2)
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
        class_name, method_name = parse_target(target, expected_parts=2)

        # Apply transformation
        self.apply_libcst_transform(
            PullUpConstructorBodyTransformer, class_name, method_name, to_class
        )


class PullUpConstructorBodyTransformer(cst.CSTTransformer):
    """Transforms a module by pulling up common constructor body to superclass."""

    def __init__(self, source_class: str, method_name: str, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            source_class: Name of the subclass containing the constructor
            method_name: Name of the method (should be __init__)
            target_class: Name of the superclass to pull the constructor to
        """
        self.source_class = source_class
        self.method_name = method_name
        self.target_class = target_class
        self.common_params: list[cst.Param] = []
        self.common_assignments: dict[str, cst.BaseExpression] = {}
        self._analyzed = False

    def visit_Module(self, node: cst.Module) -> None:  # noqa: N802
        """First pass: analyze all subclasses to find common constructor elements."""
        if self._analyzed:
            return

        subclass_info: list[dict[str, Any]] = []

        for stmt in node.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                continue
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.source_class or self._is_sibling_class(stmt):
                    info = self._extract_constructor_info(stmt)
                    if info:
                        subclass_info.append(info)

        # Find common parameters and assignments
        if subclass_info:
            self._find_common_elements(subclass_info)

        self._analyzed = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Transform class definitions to pull up constructor body."""
        if original_node.name.value == self.target_class:
            return self._add_constructor_to_superclass(updated_node)
        elif original_node.name.value == self.source_class or self._is_sibling_class(original_node):
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

    def _is_self_field_assignment(self, target: cst.AssignTarget) -> tuple[bool, str | None]:
        """Check if an assignment target is a self.field assignment.

        Args:
            target: Assignment target to check

        Returns:
            Tuple of (is_self_field_assignment, field_name or None)
        """
        if not isinstance(target.target, cst.Attribute):
            return False, None

        if not isinstance(target.target.value, cst.Name):
            return False, None

        if target.target.value.value != "self":
            return False, None

        return True, target.target.attr.value

    def _extract_constructor_info(self, class_node: cst.ClassDef) -> dict[str, Any] | None:
        """Extract constructor information from a class.

        Args:
            class_node: The class definition

        Returns:
            Dictionary with params and assignments, or None if no constructor found
        """
        init_method = find_method_in_class(class_node, self.method_name)
        if not init_method or not isinstance(init_method.body, cst.IndentedBlock):
            return None

        params: list[cst.Param] = []
        assignments: dict[str, cst.BaseExpression] = {}

        # Capture parameters (excluding self)
        for param in init_method.params.params:
            if param.name.value != "self":
                params.append(param)

        # Capture field assignments
        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for body_stmt in stmt.body:
                    if isinstance(body_stmt, cst.Assign):
                        for target in body_stmt.targets:
                            is_self_field, field_name = self._is_self_field_assignment(target)
                            if is_self_field and field_name:
                                assignments[field_name] = body_stmt.value

        return {"params": params, "assignments": assignments}

    def _find_common_elements(self, subclass_info: list[dict[str, Any]]) -> None:
        """Find common parameters and assignments across all subclasses.

        Args:
            subclass_info: List of constructor info dictionaries from subclasses
        """
        if not subclass_info:
            return

        # Start with first subclass's params and assignments
        first_info = subclass_info[0]
        common_param_names = {p.name.value for p in first_info["params"]}
        common_assignment_names = set(first_info["assignments"].keys())

        # Find intersection with other subclasses
        for info in subclass_info[1:]:
            param_names = {p.name.value for p in info["params"]}
            assignment_names = set(info["assignments"].keys())

            common_param_names &= param_names
            common_assignment_names &= assignment_names

        # Build final common params and assignments lists
        self.common_params = [p for p in first_info["params"] if p.name.value in common_param_names]
        self.common_assignments = {
            k: v for k, v in first_info["assignments"].items() if k in common_assignment_names
        }

    def _add_constructor_to_superclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Add constructor to superclass.

        Args:
            class_node: The superclass definition to modify

        Returns:
            Modified class definition
        """
        # Check if class already has __init__
        init_method = find_method_in_class(class_node, self.method_name)

        if init_method:
            # Already has constructor, don't modify
            return class_node

        # Create new __init__ with common parameters and assignments
        new_body_stmts: list[cst.BaseStatement] = []
        for field_name, value in self.common_assignments.items():
            new_body_stmts.append(create_field_assignment(field_name, value))

        new_init = cst.FunctionDef(
            name=cst.Name(self.method_name),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))] + self.common_params),
            body=cst.IndentedBlock(body=tuple(new_body_stmts)),
        )

        # Remove pass statements and add new __init__
        class_body_stmts: list[cst.BaseStatement] = []
        for stmt in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if not is_pass_statement(stmt):
                class_body_stmts.append(stmt)
        class_body_stmts.insert(0, new_init)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(class_body_stmts))
        )

    def _modify_subclass(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Modify subclass to call super().__init__() instead of setting fields directly.

        Args:
            class_node: The subclass definition to modify

        Returns:
            Modified class definition
        """
        init_method = find_method_in_class(class_node, self.method_name)
        if not init_method or not isinstance(init_method.body, cst.IndentedBlock):
            return class_node

        # Build super().__init__() call with common parameters
        super_args = [cst.Arg(value=cst.Name(param.name.value)) for param in self.common_params]
        super_call = create_super_init_call(super_args)

        # Modify __init__ to replace common assignments with super().__init__()
        new_body_stmts: list[cst.BaseStatement] = [super_call]
        common_field_names = set(self.common_assignments.keys())

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                is_common_assignment = False
                for body_stmt in stmt.body:
                    if isinstance(body_stmt, cst.Assign):
                        for target in body_stmt.targets:
                            is_self_field, field_name = self._is_self_field_assignment(target)
                            if is_self_field and field_name and field_name in common_field_names:
                                is_common_assignment = True
                                break
                if not is_common_assignment:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        modified_init = init_method.with_changes(body=cst.IndentedBlock(body=tuple(new_body_stmts)))

        # Replace init method in class body
        new_class_body: list[cst.BaseStatement] = []
        for stmt_item in class_node.body.body:
            stmt = cast(cst.BaseStatement, stmt_item)
            if stmt is init_method:
                new_class_body.append(modified_init)
            else:
                new_class_body.append(stmt)

        return class_node.with_changes(
            body=class_node.body.with_changes(body=tuple(new_class_body))
        )


# Register the command
register_command(PullUpConstructorBodyCommand)
