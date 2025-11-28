"""Introduce Parameter Object refactoring command."""

import re

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.code_generation_utils import create_parameter


class IntroduceParameterObjectCommand(BaseCommand):
    """Command to replace parameters with a parameter object."""

    name = "introduce-parameter-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "params", "name")

    def execute(self) -> None:
        """Apply introduce-parameter-object refactoring using libCST.

        Raises:
            ValueError: If function not found or target format is invalid
        """
        target = self.params["target"]
        params_str = self.params["params"]
        class_name = self.params["name"]

        # Parse comma-separated parameter names
        param_names = [p.strip() for p in params_str.split(",")]

        # Apply the transformation
        self.apply_libcst_transform(
            IntroduceParameterObjectTransformer,
            target,
            param_names,
            class_name,
        )


class IntroduceParameterObjectTransformer(cst.CSTTransformer):
    """Transforms code to replace parameters with a parameter object."""

    def __init__(self, target: str, param_names: list[str], class_name: str) -> None:
        """Initialize the transformer.

        Args:
            target: Name of the function or method to refactor
            param_names: List of parameter names to group into object
            class_name: Name of the new parameter object class
        """
        self.target = target
        self.param_names = param_names
        self.class_name = class_name
        # Convert class name to snake_case for parameter name
        self.new_param_name = self._class_name_to_snake_case(class_name)
        self.class_inserted = False

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and insert the new parameter object class."""
        if self.class_inserted:
            return updated_node

        # Create the new parameter object class
        param_class = self._create_parameter_class()

        # Find insertion point: after imports and first class (Charge)
        insertion_index = 0
        found_first_class = False
        for i, stmt in enumerate(updated_node.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                # After imports
                insertion_index = i + 1
            elif isinstance(stmt, cst.ClassDef) and not found_first_class:
                # After the first class
                insertion_index = i + 1
                found_first_class = True

        # Insert the new class
        new_body = list(updated_node.body)
        new_body.insert(insertion_index, param_class)

        self.class_inserted = True
        return updated_node.with_changes(body=new_body)

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and update parameters if it's the target function."""
        if original_node.name.value != self.target:
            return updated_node

        # Replace parameters: keep non-target params, and insert new param where first target was
        new_params = []
        replaced = False
        for param in original_node.params.params:
            if param.name.value in self.param_names:
                # Replace the first occurrence with the new parameter
                if not replaced:
                    new_params.append(create_parameter(self.new_param_name))
                    replaced = True
                # Skip other target parameters
            else:
                # Keep non-target parameters
                new_params.append(param)

        # Update the function body to use the parameter object
        updated_node = updated_node.with_changes(
            params=updated_node.params.with_changes(params=new_params)
        )

        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Leave call and update calls to the target function."""
        # Check if this is a call to our target function
        if not (isinstance(updated_node.func, cst.Name) and updated_node.func.value == self.target):
            return updated_node

        # Find the arguments that correspond to our parameters
        args = list(updated_node.args)
        if len(args) < len(self.param_names):
            return updated_node

        # Collect the arguments to replace
        args_to_replace = []
        remaining_args = []
        replaced_count = 0

        for i, arg in enumerate(args):
            if replaced_count < len(self.param_names):
                args_to_replace.append(arg.value)
                replaced_count += 1
            else:
                remaining_args.append(arg)

        # Create the constructor call for the parameter object
        constructor_call = cst.Call(
            func=cst.Name(self.class_name),
            args=[cst.Arg(value=arg) for arg in args_to_replace],
        )

        # Build the new argument list
        new_args = [cst.Arg(value=constructor_call)] + remaining_args

        return updated_node.with_changes(args=new_args)

    def leave_Comparison(  # noqa: N802
        self, original_node: cst.Comparison, updated_node: cst.Comparison
    ) -> cst.BaseExpression:
        """Leave comparison and update parameter references."""
        # Check if this is a comparison with our target parameters
        # e.g., start_date <= charge.date <= end_date
        # Should become: date_range.includes(charge.date)

        # Look for the pattern: param1 <= expr <= param2
        if len(updated_node.comparisons) == 2:
            left_comp = updated_node.comparisons[0]
            right_comp = updated_node.comparisons[1]

            left_is_param = (
                isinstance(updated_node.left, cst.Name)
                and updated_node.left.value in self.param_names
            )
            right_is_param = (
                isinstance(right_comp.comparator, cst.Name)
                and right_comp.comparator.value in self.param_names
            )

            if (
                left_is_param
                and right_is_param
                and isinstance(left_comp.operator, cst.LessThanEqual)
                and isinstance(right_comp.operator, cst.LessThanEqual)
            ):
                # Replace with date_range.includes(charge.date)
                return cst.Call(
                    func=cst.Attribute(
                        value=cst.Name(self.new_param_name),
                        attr=cst.Name("includes"),
                    ),
                    args=[cst.Arg(left_comp.comparator)],
                )

        return updated_node

    def _create_parameter_class(self) -> cst.ClassDef:
        """Create the new parameter object class.

        Returns:
            The new class definition
        """
        param_mapping = {
            param_name: self._get_short_field_name(param_name) for param_name in self.param_names
        }

        init_method = self._create_init_method(param_mapping)
        includes_method = self._create_includes_method()

        # Create the class
        return cst.ClassDef(
            name=cst.Name(self.class_name),
            body=cst.IndentedBlock(
                body=[
                    init_method,
                    cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),  # type: ignore[list-item]
                    includes_method,
                ]
            ),
            leading_lines=[
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            ],
        )

    def _create_init_method(self, param_mapping: dict[str, str]) -> cst.FunctionDef:
        """Create the __init__ method for the parameter object.

        Args:
            param_mapping: Mapping from original parameter names to short field names

        Returns:
            The __init__ method definition
        """
        # Create __init__ method parameters
        init_params = [create_parameter("self")]
        for short_name in param_mapping.values():
            init_params.append(create_parameter(short_name))

        # Create field assignments for __init__
        init_body = []
        for param_name in self.param_names:
            short_name = param_mapping[param_name]
            init_body.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(short_name),
                                    )
                                )
                            ],
                            value=cst.Name(short_name),
                        )
                    ]
                )
            )

        return cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=init_params),
            body=cst.IndentedBlock(body=init_body),
        )

    def _create_includes_method(self) -> cst.FunctionDef:
        """Create the includes method for range checking.

        Returns:
            The includes method definition
        """
        return cst.FunctionDef(
            name=cst.Name("includes"),
            params=cst.Parameters(
                params=[
                    create_parameter("self"),
                    create_parameter("date"),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Comparison(
                                    left=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name("start"),
                                    ),
                                    comparisons=[
                                        cst.ComparisonTarget(
                                            operator=cst.LessThanEqual(),
                                            comparator=cst.Name("date"),
                                        ),
                                        cst.ComparisonTarget(
                                            operator=cst.LessThanEqual(),
                                            comparator=cst.Attribute(
                                                value=cst.Name("self"),
                                                attr=cst.Name("end"),
                                            ),
                                        ),
                                    ],
                                )
                            )
                        ]
                    )
                ]
            ),
        )

    def _class_name_to_snake_case(self, class_name: str) -> str:
        """Convert a class name from PascalCase to snake_case.

        Args:
            class_name: The class name in PascalCase

        Returns:
            The class name in snake_case
        """
        # Insert underscores before uppercase letters (except the first one)
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
        return snake_case

    def _get_short_field_name(self, param_name: str) -> str:
        """Get shortened field name by removing common prefixes.

        Args:
            param_name: The original parameter name

        Returns:
            The shortened field name for use in the parameter object
        """
        # Remove common prefixes like "start_" and "end_"
        if param_name.startswith("start_"):
            return "start"
        elif param_name.startswith("end_"):
            return "end"
        else:
            return param_name


# Register the command
register_command(IntroduceParameterObjectCommand)
