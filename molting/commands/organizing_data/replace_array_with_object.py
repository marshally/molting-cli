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
        new_param_name = self._derive_parameter_name()
        updated_node = self._rename_parameter(updated_node, new_param_name)

        # Replace array accesses with attribute accesses
        replacer = ArrayAccessReplacer(self.param_name, new_param_name, self.field_names)
        updated_node = cast(cst.FunctionDef, updated_node.visit(replacer))

        return updated_node

    def _derive_parameter_name(self) -> str:
        """Derive parameter name from class name.

        Returns:
            Parameter name (lowercase version of class name)
        """
        return self.new_class_name.lower()

    def _rename_parameter(self, function: cst.FunctionDef, new_name: str) -> cst.FunctionDef:
        """Rename the target parameter in function signature.

        Args:
            function: The function definition
            new_name: The new parameter name

        Returns:
            Function with renamed parameter
        """
        new_params = []
        for param in function.params.params:
            if isinstance(param.name, cst.Name) and param.name.value == self.param_name:
                new_params.append(param.with_changes(name=cst.Name(new_name)))
            else:
                new_params.append(param)

        return function.with_changes(params=function.params.with_changes(params=new_params))

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
                self._process_assignment(stmt)

    def _process_assignment(self, assign: cst.Assign) -> None:
        """Process an assignment to extract field name from array access.

        Args:
            assign: The assignment statement
        """
        if not isinstance(assign.value, cst.Subscript):
            return

        if not self._is_array_subscript(assign.value):
            return

        index = self._extract_index(assign.value)
        if index is None:
            return

        variable_name = self._extract_variable_name(assign)
        if variable_name is not None:
            self.accesses[index] = variable_name

    def _is_array_subscript(self, subscript: cst.Subscript) -> bool:
        """Check if subscript is accessing our target array parameter.

        Args:
            subscript: The subscript node to check

        Returns:
            True if subscript accesses the target array
        """
        return isinstance(subscript.value, cst.Name) and subscript.value.value == self.param_name

    def _extract_index(self, subscript: cst.Subscript) -> int | None:
        """Extract integer index from subscript.

        Args:
            subscript: The subscript node

        Returns:
            Integer index or None if not an integer index
        """
        if not isinstance(subscript.slice[0].slice, cst.Index):
            return None

        index_value = subscript.slice[0].slice.value
        if not isinstance(index_value, cst.Integer):
            return None

        return int(index_value.value)

    def _extract_variable_name(self, assign: cst.Assign) -> str | None:
        """Extract variable name from assignment target.

        Args:
            assign: The assignment statement

        Returns:
            Variable name or None if target is not a simple name
        """
        if len(assign.targets) == 0:
            return None

        target = assign.targets[0].target
        if not isinstance(target, cst.Name):
            return None

        return target.value

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
        if not self._is_target_array_access(updated_node):
            return updated_node

        index = self._extract_subscript_index(updated_node)
        if index is None or index >= len(self.field_names):
            return updated_node

        return self._create_attribute_access(index)

    def _is_target_array_access(self, subscript: cst.Subscript) -> bool:
        """Check if subscript accesses the target array parameter.

        Args:
            subscript: The subscript node to check

        Returns:
            True if this is accessing the old array parameter
        """
        return (
            isinstance(subscript.value, cst.Name) and subscript.value.value == self.old_param_name
        )

    def _extract_subscript_index(self, subscript: cst.Subscript) -> int | None:
        """Extract the integer index from a subscript.

        Args:
            subscript: The subscript node

        Returns:
            Integer index or None if not an integer subscript
        """
        if not isinstance(subscript.slice[0].slice, cst.Index):
            return None

        index_value = subscript.slice[0].slice.value
        if not isinstance(index_value, cst.Integer):
            return None

        return int(index_value.value)

    def _create_attribute_access(self, index: int) -> cst.Attribute:
        """Create attribute access for the given index.

        Args:
            index: The array index to convert

        Returns:
            Attribute access node
        """
        return cst.Attribute(
            value=cst.Name(self.new_param_name),
            attr=cst.Name(self.field_names[index]),
        )


# Register the command
register_command(ReplaceArrayWithObjectCommand)
