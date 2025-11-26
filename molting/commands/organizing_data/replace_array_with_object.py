"""Replace Array with Object refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter


class ReplaceArrayWithObjectCommand(BaseCommand):
    """Command to replace an array with an object that has a field for each element."""

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
        self.array_accesses: list[tuple[int, str]] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Visit function definitions to find array accesses.

        Args:
            node: The function definition node

        Returns:
            True to continue visiting children
        """
        if node.name.value == self.function_name:
            # Scan the function body to find array accesses
            self._scan_for_array_accesses(node)
        return True

    def _scan_for_array_accesses(self, func_def: cst.FunctionDef) -> None:
        """Scan function body to identify array accesses and their indices.

        Args:
            func_def: The function definition to scan
        """
        scanner = ArrayAccessScanner(self.param_name)
        func_def.visit(scanner)
        self.array_accesses = scanner.accesses

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the new class to the module.

        Args:
            original_node: The original module
            updated_node: The updated module

        Returns:
            Modified module with new class
        """
        new_class = self._create_new_class()
        modified_statements: list[cst.BaseStatement] = [
            new_class,
            cast(cst.BaseStatement, cst.EmptyLine()),
            cast(cst.BaseStatement, cst.EmptyLine()),
        ]

        modified_statements.extend(updated_node.body)

        return updated_node.with_changes(body=tuple(modified_statements))

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform the function to use object attributes instead of array indices.

        Args:
            original_node: The original function
            updated_node: The updated function

        Returns:
            Modified function
        """
        if updated_node.name.value != self.function_name:
            return updated_node

        # First, transform array accesses to object attribute accesses
        transformer = ArrayToObjectTransformer(self.param_name, self.array_accesses)
        updated_func = cast(cst.FunctionDef, updated_node.visit(transformer))

        # Then, rename the parameter to use the lowercase version of the class name
        new_param_name = self.new_class_name.lower()
        updated_func = self._rename_parameter(updated_func, self.param_name, new_param_name)

        return updated_func

    def _rename_parameter(
        self, func_def: cst.FunctionDef, old_name: str, new_name: str
    ) -> cst.FunctionDef:
        """Rename a parameter in a function.

        Args:
            func_def: The function definition
            old_name: The old parameter name
            new_name: The new parameter name

        Returns:
            Modified function definition
        """
        # Update parameters
        new_params = []
        for param in func_def.params.params:
            if param.name.value == old_name:
                new_params.append(param.with_changes(name=cst.Name(new_name)))
            else:
                new_params.append(param)

        updated_params = func_def.params.with_changes(params=new_params)

        # Update references in the body
        renamer = NameRenamer(old_name, new_name)
        new_body = func_def.body.visit(renamer)

        return func_def.with_changes(params=updated_params, body=new_body)

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new class with fields for each array element.

        Returns:
            New class definition
        """
        # Sort accesses by index to maintain consistent order
        sorted_accesses = sorted(self.array_accesses, key=lambda x: x[0])

        # Create parameters for __init__
        params = [create_parameter("self")]
        for _, var_name in sorted_accesses:
            params.append(create_parameter(var_name))

        # Create assignment statements for __init__
        assignments: list[cst.SimpleStatementLine] = []
        for _, var_name in sorted_accesses:
            assignments.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(var_name),
                                    )
                                )
                            ],
                            value=cst.Name(var_name),
                        )
                    ]
                )
            )

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=params),
            body=cst.IndentedBlock(body=assignments),
        )

        return cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[],
            body=cst.IndentedBlock(body=[init_method]),
        )


class ArrayAccessScanner(cst.CSTVisitor):
    """Scans for array accesses to determine field names."""

    def __init__(self, param_name: str) -> None:
        """Initialize the scanner.

        Args:
            param_name: Name of the array parameter
        """
        self.param_name = param_name
        self.accesses: list[tuple[int, str]] = []

    def visit_Assign(self, node: cst.Assign) -> None:  # noqa: N802
        """Visit assignment nodes to find array accesses.

        Args:
            node: The assignment node
        """
        # Check if the value is a subscript of our parameter
        if isinstance(node.value, cst.Subscript):
            if isinstance(node.value.value, cst.Name) and node.value.value.value == self.param_name:
                # Extract the index
                for subscript_element in node.value.slice:
                    if isinstance(subscript_element.slice, cst.Index):
                        index_value = subscript_element.slice.value
                        if isinstance(index_value, cst.Integer):
                            index = int(index_value.value)
                            # Get the target variable name
                            for target in node.targets:
                                if isinstance(target.target, cst.Name):
                                    var_name = target.target.value
                                    self.accesses.append((index, var_name))


class ArrayToObjectTransformer(cst.CSTTransformer):
    """Transforms array subscript access to object attribute access."""

    def __init__(self, param_name: str, accesses: list[tuple[int, str]]) -> None:
        """Initialize the transformer.

        Args:
            param_name: Name of the array parameter
            accesses: List of (index, variable_name) tuples
        """
        self.param_name = param_name
        self.index_to_var = {index: var_name for index, var_name in accesses}

    def leave_Assign(  # noqa: N802
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> cst.Assign:
        """Transform array access assignments to object attribute access.

        Args:
            original_node: The original assignment
            updated_node: The updated assignment

        Returns:
            Modified assignment
        """
        if isinstance(updated_node.value, cst.Subscript):
            if (
                isinstance(updated_node.value.value, cst.Name)
                and updated_node.value.value.value == self.param_name
            ):
                # Get the index
                for subscript_element in updated_node.value.slice:
                    if isinstance(subscript_element.slice, cst.Index):
                        index_value = subscript_element.slice.value
                        if isinstance(index_value, cst.Integer):
                            index = int(index_value.value)
                            if index in self.index_to_var:
                                var_name = self.index_to_var[index]
                                # Replace row[index] with row.var_name
                                new_value = cst.Attribute(
                                    value=cst.Name(self.param_name),
                                    attr=cst.Name(var_name),
                                )
                                return updated_node.with_changes(value=new_value)

        return updated_node


class NameRenamer(cst.CSTTransformer):
    """Renames all references to a name in the AST."""

    def __init__(self, old_name: str, new_name: str) -> None:
        """Initialize the renamer.

        Args:
            old_name: The old name to replace
            new_name: The new name to use
        """
        self.old_name = old_name
        self.new_name = new_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:  # noqa: N802
        """Rename name nodes.

        Args:
            original_node: The original name node
            updated_node: The updated name node

        Returns:
            Modified name node
        """
        if updated_node.value == self.old_name:
            return updated_node.with_changes(value=self.new_name)
        return updated_node


# Register the command
register_command(ReplaceArrayWithObjectCommand)
