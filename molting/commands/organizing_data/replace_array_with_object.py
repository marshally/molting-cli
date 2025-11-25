"""Replace Array with Object refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter


class ReplaceArrayWithObjectCommand(BaseCommand):
    """Command to replace an array with an object."""

    name = "replace-array-with-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for replace-array-with-object: 'target'")
        if "name" not in self.params:
            raise ValueError("Missing required parameter for replace-array-with-object: 'name'")

    def execute(self) -> None:
        """Apply replace-array-with-object refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        new_class_name = self.params["name"]

        # Parse the target to get function and parameter names
        function_name, param_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ReplaceArrayWithObjectTransformer(function_name, param_name, new_class_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceArrayWithObjectTransformer(cst.CSTTransformer):
    """Transforms array access to object attribute access."""

    def __init__(self, function_name: str, param_name: str, new_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function containing the array parameter
            param_name: Name of the array parameter to replace
            new_class_name: Name of the new class to create
        """
        self.function_name = function_name
        self.param_name = param_name
        self.new_class_name = new_class_name
        self.field_names: list[str] = []

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the new class to the module."""
        new_class = self._create_new_class()
        modified_statements: list[cst.BaseStatement] = [
            new_class,
            cast(cst.BaseStatement, cst.EmptyLine()),
        ]

        for stmt in updated_node.body:
            modified_statements.append(stmt)

        return updated_node.with_changes(body=tuple(modified_statements))

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform function to use object instead of array."""
        if updated_node.name.value != self.function_name:
            return updated_node

        # Collect field names from array subscripts
        collector = ArrayAccessCollector(self.param_name)
        original_node.visit(collector)
        self.field_names = collector.get_field_names()

        # Rename parameter
        new_param_name = self.new_class_name.lower()
        new_params = []
        for param in updated_node.params.params:
            if isinstance(param.name, cst.Name) and param.name.value == self.param_name:
                new_params.append(param.with_changes(name=cst.Name(new_param_name)))
            else:
                new_params.append(param)

        updated_node = updated_node.with_changes(
            params=updated_node.params.with_changes(params=new_params)
        )

        # Replace array accesses with attribute accesses
        replacer = ArrayAccessReplacer(self.param_name, new_param_name, self.field_names)
        updated_node = cast(cst.FunctionDef, updated_node.visit(replacer))

        return updated_node

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new class.

        Returns:
            New class definition
        """
        # Create __init__ parameters
        init_params = [create_parameter("self")]
        init_assignments = []

        for field_name in self.field_names:
            init_params.append(create_parameter(field_name))
            init_assignments.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(field_name),
                                    )
                                )
                            ],
                            value=cst.Name(field_name),
                        )
                    ]
                )
            )

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=init_params),
            body=cst.IndentedBlock(body=init_assignments),
        )

        return cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[],
            body=cst.IndentedBlock(body=[init_method]),
        )


class ArrayAccessCollector(cst.CSTVisitor):
    """Collects array access patterns to determine field names."""

    def __init__(self, param_name: str) -> None:
        """Initialize the collector.

        Args:
            param_name: Name of the array parameter
        """
        self.param_name = param_name
        self.accesses: dict[int, str] = {}

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:  # noqa: N802
        """Visit assignment statements to extract field names from variable names.

        Args:
            node: The statement line node
        """
        for stmt in node.body:
            if isinstance(stmt, cst.Assign):
                # Check if right side is array subscript
                if isinstance(stmt.value, cst.Subscript):
                    if (
                        isinstance(stmt.value.value, cst.Name)
                        and stmt.value.value.value == self.param_name
                    ):
                        if isinstance(stmt.value.slice[0].slice, cst.Index):
                            index_value = stmt.value.slice[0].slice.value
                            if isinstance(index_value, cst.Integer):
                                index = int(index_value.value)
                                # Extract variable name from left side
                                if len(stmt.targets) > 0:
                                    target = stmt.targets[0].target
                                    if isinstance(target, cst.Name):
                                        self.accesses[index] = target.value

    def get_field_names(self) -> list[str]:
        """Get the collected field names in order.

        Returns:
            List of field names
        """
        if not self.accesses:
            return []
        max_index = max(self.accesses.keys())
        return [self.accesses.get(i, f"field_{i}") for i in range(max_index + 1)]


class ArrayAccessReplacer(cst.CSTTransformer):
    """Replaces array accesses with attribute accesses."""

    def __init__(self, old_param_name: str, new_param_name: str, field_names: list[str]) -> None:
        """Initialize the replacer.

        Args:
            old_param_name: Original array parameter name
            new_param_name: New object parameter name
            field_names: List of field names to use
        """
        self.old_param_name = old_param_name
        self.new_param_name = new_param_name
        self.field_names = field_names

    def leave_Subscript(  # noqa: N802
        self, original_node: cst.Subscript, updated_node: cst.Subscript
    ) -> cst.BaseExpression:
        """Replace array subscripts with attribute access.

        Args:
            original_node: The original subscript node
            updated_node: The updated subscript node

        Returns:
            Attribute access or original subscript
        """
        if isinstance(updated_node.value, cst.Name):
            if updated_node.value.value == self.old_param_name:
                if isinstance(updated_node.slice[0].slice, cst.Index):
                    index_value = updated_node.slice[0].slice.value
                    if isinstance(index_value, cst.Integer):
                        index = int(index_value.value)
                        if index < len(self.field_names):
                            return cst.Attribute(
                                value=cst.Name(self.new_param_name),
                                attr=cst.Name(self.field_names[index]),
                            )
        return updated_node


# Register the command
register_command(ReplaceArrayWithObjectCommand)
