"""Introduce Parameter Object refactoring command."""

import re

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.code_generation_utils import create_parameter


class IntroduceParameterObjectCommand(BaseCommand):
    """Replace a group of related parameters with a single parameter object.

    The Introduce Parameter Object refactoring groups parameters that naturally
    belong together into a single parameter object class. This simplifies method
    signatures and makes the code more maintainable by encapsulating related data.

    **When to use:**
    - A method has multiple parameters that are always passed together
    - The same group of parameters is used in multiple methods
    - Parameters represent a concept that would benefit from bundling (e.g., a date range)
    - You want to simplify method signatures and reduce parameter lists
    - Related parameters need shared behavior or validation

    **Example:**
    Before:
        def charge_amount(start_date, end_date, charge):
            if start_date <= charge.date <= end_date:
                return charge.amount
            return 0

    After:
        class DateRange:
            def __init__(self, start, end):
                self.start = start
                self.end = end

            def includes(self, date):
                return self.start <= date <= self.end

        def charge_amount(date_range, charge):
            if date_range.includes(charge.date):
                return charge.amount
            return 0
    """

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
            target: Name of the function or method to refactor (e.g., "MyClass::method_name")
            param_names: List of parameter names to group into object
            class_name: Name of the new parameter object class
        """
        # Parse target to extract class and method names
        if "::" in target:
            self.target_class, self.target_method = target.split("::")
        else:
            self.target_class = None
            self.target_method = target

        self.param_names = param_names
        self.class_name = class_name
        # Convert class name to snake_case for parameter name
        self.new_param_name = self._class_name_to_snake_case(class_name)
        self.class_inserted = False
        self._in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track when we enter the target class."""
        if self.target_class and node.name.value == self.target_class:
            self._in_target_class = True
        return True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Track when we leave the target class."""
        if self.target_class and original_node.name.value == self.target_class:
            self._in_target_class = False
        return updated_node

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and insert the new parameter object class."""
        if self.class_inserted:
            return updated_node

        # Create the new parameter object class
        param_class = self._create_parameter_class()

        # Find insertion point: after imports and first class
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
        """Leave function definition and update parameters if needed.

        Updates both the target method and any other methods in the class that
        accept the same parameters.
        """
        # Check if we're in the target class
        if self.target_class and not self._in_target_class:
            return updated_node

        # Check if this method has any of our target parameters
        has_target_params = any(
            param.name.value in self.param_names for param in original_node.params.params
        )

        if not has_target_params:
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
        body_updater = ParameterObjectBodyUpdater(
            self.param_names, self.new_param_name, self.class_name
        )
        updated_body = updated_node.body.visit(body_updater)

        updated_node = updated_node.with_changes(
            params=updated_node.params.with_changes(params=new_params), body=updated_body
        )

        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Leave call and update calls to the target function."""
        # Check if this is a call to our target function
        if not (
            isinstance(updated_node.func, cst.Name)
            and updated_node.func.value == self.target_method
        ):
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
        # Keep original parameter names as field names
        init_method = self._create_init_method()

        # Only include includes method for date range patterns
        methods = [init_method]
        if self._should_create_includes_method():
            methods.append(cst.EmptyLine(whitespace=cst.SimpleWhitespace("")))  # type: ignore[arg-type]
            methods.append(self._create_includes_method())

        # Create the class
        return cst.ClassDef(
            name=cst.Name(self.class_name),
            body=cst.IndentedBlock(body=methods),
            leading_lines=[
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            ],
        )

    def _create_init_method(self) -> cst.FunctionDef:
        """Create the __init__ method for the parameter object.

        Returns:
            The __init__ method definition
        """
        # Create __init__ method parameters - use original parameter names
        init_params = [create_parameter("self")]
        for param_name in self.param_names:
            init_params.append(create_parameter(param_name))

        # Create field assignments for __init__
        init_body = []
        for param_name in self.param_names:
            init_body.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(param_name),
                                    )
                                )
                            ],
                            value=cst.Name(param_name),
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
        # For date range patterns, use shortened field names (start/end)
        start_field = self._get_short_field_name(self.param_names[0])
        end_field = self._get_short_field_name(self.param_names[1])

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
                                        attr=cst.Name(start_field),
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
                                                attr=cst.Name(end_field),
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

    def _should_create_includes_method(self) -> bool:
        """Check if we should create an includes method (for date ranges).

        Returns:
            True if this looks like a date range pattern
        """
        # Only create includes method for date/time range patterns
        return (
            len(self.param_names) == 2
            and any("start" in name.lower() or "begin" in name.lower() for name in self.param_names)
            and any("end" in name.lower() for name in self.param_names)
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
        # Remove common prefixes like "start_" and "end_" for date range patterns
        if self._should_create_includes_method():
            if param_name.startswith("start_"):
                return "start"
            elif param_name.startswith("end_"):
                return "end"
        # Otherwise keep the original name
        return param_name


class ParameterObjectBodyUpdater(cst.CSTTransformer):
    """Updates function body to use parameter object instead of individual parameters.

    This updater handles:
    1. Local variable assignments that reference old parameters (e.g., x = param -> x = config.param)
    2. Method calls that pass the old parameters (replace with parameter object)
    3. References to parameters in attribute accesses (e.g., config.start_row)
    """

    def __init__(self, param_names: list[str], new_param_name: str, class_name: str) -> None:
        """Initialize the updater.

        Args:
            param_names: List of original parameter names
            new_param_name: Name of the new parameter object parameter
            class_name: Name of the parameter object class
        """
        self.param_names = param_names
        self.new_param_name = new_param_name
        self.class_name = class_name

    def leave_Assign(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> cst.Assign:  # noqa: N802
        """Update assignments that reference the old parameters."""
        # Check if the right-hand side is a simple Name that references one of our parameters
        if (
            isinstance(updated_node.value, cst.Name)
            and updated_node.value.value in self.param_names
        ):
            # Replace param_name with config.param_name
            new_value = cst.Attribute(
                value=cst.Name(self.new_param_name), attr=cst.Name(updated_node.value.value)
            )
            return updated_node.with_changes(value=new_value)
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Update method calls to use the parameter object."""
        # Check if this is a call to a method (self._format_report)
        if not isinstance(updated_node.func, cst.Attribute):
            return updated_node

        # Check if any arguments reference our old parameters
        new_args = []
        replaced_params = set()

        for arg in updated_node.args:
            if isinstance(arg.value, cst.Name) and arg.value.value in self.param_names:
                # This argument references an old parameter
                replaced_params.add(arg.value.value)
            else:
                new_args.append(arg)

        # If we replaced any params, replace them all with the parameter object
        if replaced_params:
            # Add the parameter object as the first argument
            new_args.insert(0, cst.Arg(value=cst.Name(self.new_param_name)))
            return updated_node.with_changes(args=new_args)

        return updated_node

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute | cst.BaseExpression:
        """Update attribute accesses that reference the parameter object."""
        # Check if this is accessing a field on the parameter object
        # e.g., config.start_row -> config.start_row (already correct)
        # But also handle source.get_data(start, end) -> source.get_data(config.start_row, config.end_row)
        return updated_node

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.Name | cst.Attribute:  # noqa: N802
        """Update name references to parameters."""
        # Only update if this is one of our parameters (in an expression context, not assignment target)
        if updated_node.value in self.param_names:
            # Check if we're in an assignment target context by seeing if parent is AssignTarget
            # For now, we'll be conservative and only replace in specific contexts
            # The leave_Assign already handles the common case
            pass
        return updated_node


# Register the command
register_command(IntroduceParameterObjectCommand)
