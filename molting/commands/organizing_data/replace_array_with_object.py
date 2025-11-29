"""Replace Array with Object refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter
from molting.core.name_conflict_validator import NameConflictValidator


class ReplaceArrayWithObjectCommand(BaseCommand):
    """Replace an array parameter with an object that has named fields.

    This refactoring transforms array-based parameters where different indices
    represent different semantic values into objects with explicit named fields.
    Arrays used this way are difficult to understand because it's unclear what
    each array element represents. By replacing the array with an object, you
    make the code more explicit and maintainable.

    **When to use:**
    - You have an array parameter where different elements represent different
      things (e.g., array[0] is name, array[1] is age, array[2] is email)
    - You want to make code more readable by using named fields instead of
      magic indices
    - You're dealing with fixed-size arrays passed as parameters
    - You want to improve type safety and self-documenting code

    **Example:**

    Before:
        def process_person(data):
            name = data[0]
            age = data[1]
            email = data[2]
            return f"{name} ({age}): {email}"

    After:
        class PersonData:
            def __init__(self, name, age, email):
                self.name = name
                self.age = age
                self.email = email

        def process_person(person_data):
            return f"{person_data.name} ({person_data.age}): {person_data.email}"
    """

    name = "replace-array-with-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

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

        # Check for name conflicts before applying transformation
        validator = NameConflictValidator(source_code)
        validator.validate_class_name(new_class_name)

        module = cst.parse_module(source_code)

        # First pass: collect all array accesses to determine field names
        collector = ArrayAccessCollector(function_name, param_name)
        module.visit(collector)
        field_names = collector.field_names

        # Second pass: transform the code
        transformer = ReplaceArrayWithObjectTransformer(
            function_name, param_name, new_class_name, field_names
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceArrayWithObjectTransformer(cst.CSTTransformer):
    """Transforms an array parameter into an object with named fields."""

    def __init__(
        self, function_name: str, param_name: str, new_class_name: str, field_names: list[str]
    ) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function containing the parameter
            param_name: Name of the array parameter to replace
            new_class_name: Name of the new class to create
            field_names: List of field names for the new class
        """
        self.function_name = function_name
        self.param_name = param_name
        self.new_class_name = new_class_name
        self.field_names = field_names
        self.in_target_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:  # noqa: N802
        """Track when we're inside the target function.

        Args:
            node: The function definition node

        Returns:
            True to continue visiting children
        """
        if node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave the function definition.

        Args:
            original_node: The original function node
            updated_node: The updated function node

        Returns:
            The function node, potentially modified
        """
        if original_node.name.value == self.function_name:
            self.in_target_function = False
        return updated_node

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the new class to the module.

        Args:
            original_node: The original module node
            updated_node: The updated module node

        Returns:
            Modified module with new class prepended
        """
        # Create the new class
        new_class = self._create_new_class()
        modified_statements: list[cst.BaseStatement] = [
            new_class,
            cast(cst.BaseStatement, cst.EmptyLine()),
            cast(cst.BaseStatement, cst.EmptyLine()),
        ]

        # Add all original statements
        for stmt in updated_node.body:
            modified_statements.append(stmt)

        return updated_node.with_changes(body=tuple(modified_statements))

    def leave_Subscript(  # noqa: N802
        self, original_node: cst.Subscript, updated_node: cst.Subscript
    ) -> cst.BaseExpression:
        """Replace array subscript access with attribute access.

        Args:
            original_node: The original subscript node
            updated_node: The updated subscript node

        Returns:
            Modified expression (attribute access) or original node
        """
        if not self.in_target_function:
            return updated_node

        # Check if this is accessing our array parameter
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value == self.param_name:
            # Extract the index
            if isinstance(updated_node.slice, (list, tuple)) and len(updated_node.slice) > 0:
                index_node = updated_node.slice[0]
                if isinstance(index_node.slice, cst.Index):
                    if isinstance(index_node.slice.value, cst.Integer):
                        index = int(index_node.slice.value.value)
                        if index < len(self.field_names):
                            field_name = self.field_names[index]
                            # Convert parameter name to lowercase for the object reference
                            object_name = self.new_class_name.lower()
                            return cst.Attribute(
                                value=cst.Name(object_name),
                                attr=cst.Name(field_name),
                            )

        return updated_node

    def leave_Param(  # noqa: N802
        self, original_node: cst.Param, updated_node: cst.Param
    ) -> cst.Param:
        """Replace the array parameter with the new object parameter.

        Args:
            original_node: The original parameter node
            updated_node: The updated parameter node

        Returns:
            Modified parameter or original
        """
        if not self.in_target_function:
            return updated_node

        if updated_node.name.value == self.param_name:
            # Replace parameter name with lowercase class name
            new_name = self.new_class_name.lower()
            return updated_node.with_changes(name=cst.Name(new_name))

        return updated_node

    def _create_new_class(self) -> cst.ClassDef:
        """Create the new class with fields for each array element.

        Returns:
            New class definition
        """
        # Create __init__ method
        params = [create_parameter("self")]
        init_body_stmts: list[cst.BaseStatement] = []

        for field_name in self.field_names:
            params.append(create_parameter(field_name))
            # Add assignment in __init__
            init_body_stmts.append(
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
            params=cst.Parameters(params=params),
            body=cst.IndentedBlock(body=init_body_stmts),
        )

        return cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[],
            body=cst.IndentedBlock(body=[init_method]),
        )


class ArrayAccessCollector(cst.CSTVisitor):
    """Collects array accesses to determine field names."""

    def __init__(self, function_name: str, param_name: str) -> None:
        """Initialize the collector.

        Args:
            function_name: Name of the function containing the parameter
            param_name: Name of the array parameter
        """
        self.function_name = function_name
        self.param_name = param_name
        self.field_names: list[str] = []
        self.in_target_function = False
        self.assignments: dict[int, str] = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:  # noqa: N802
        """Track when we're inside the target function.

        Args:
            node: The function definition node

        Returns:
            True to continue visiting children
        """
        if node.name.value == self.function_name:
            self.in_target_function = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Leave the function definition.

        Args:
            node: The function definition node
        """
        if node.name.value == self.function_name:
            self.in_target_function = False
            # Build field names list from assignments
            if self.assignments:
                max_index = max(self.assignments.keys())
                self.field_names = []
                for i in range(max_index + 1):
                    self.field_names.append(self.assignments.get(i, f"field_{i}"))

    def visit_Assign(self, node: cst.Assign) -> bool | None:  # noqa: N802
        """Visit assignment nodes to extract field names from variable assignments.

        Args:
            node: The assign node

        Returns:
            True to continue visiting
        """
        if not self.in_target_function:
            return True

        # Check if the value is a subscript access to our parameter
        if isinstance(node.value, cst.Subscript):
            if isinstance(node.value.value, cst.Name) and node.value.value.value == self.param_name:
                # Extract the index
                if isinstance(node.value.slice, (list, tuple)) and len(node.value.slice) > 0:
                    index_node = node.value.slice[0]
                    if isinstance(index_node.slice, cst.Index):
                        if isinstance(index_node.slice.value, cst.Integer):
                            index = int(index_node.slice.value.value)
                            # Extract the variable name being assigned to
                            for target in node.targets:
                                if isinstance(target.target, cst.Name):
                                    var_name = target.target.value
                                    self.assignments[index] = var_name

        return True


# Register the command
register_command(ReplaceArrayWithObjectCommand)
