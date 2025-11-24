"""Introduce Parameter Object refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


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
                    new_params.append(
                        cst.Param(
                            name=cst.Name(self.new_param_name),
                        )
                    )
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
        # Create __init__ method parameters
        init_params = [cst.Param(name=cst.Name("self"))]

        # Map original parameter names to shorter versions for the class
        param_mapping = {}
        for param_name in self.param_names:
            # Remove common prefixes like "start_" and "end_"
            if param_name.startswith("start_"):
                short_name = "start"
            elif param_name.startswith("end_"):
                short_name = "end"
            else:
                short_name = param_name
            param_mapping[param_name] = short_name
            init_params.append(cst.Param(name=cst.Name(short_name)))

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

        # Create __init__ method
        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=init_params),
            body=cst.IndentedBlock(body=init_body),
        )

        # Create includes method
        includes_method = cst.FunctionDef(
            name=cst.Name("includes"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(name=cst.Name("date")),
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

        # Create the class
        return cst.ClassDef(
            name=cst.Name(self.class_name),
            body=cst.IndentedBlock(
                body=[
                    init_method,
                    cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                    includes_method,
                ]
            ),
            leading_lines=[
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            ],
        )

    def _class_name_to_snake_case(self, class_name: str) -> str:
        """Convert a class name from PascalCase to snake_case.

        Args:
            class_name: The class name in PascalCase

        Returns:
            The class name in snake_case
        """
        # Insert underscores before uppercase letters (except the first one)
        import re

        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
        return snake_case


# Register the command
register_command(IntroduceParameterObjectCommand)
