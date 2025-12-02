"""Introduce Parameter Object refactoring command."""

import re
from typing import Optional

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
            target: Name of the function or method to refactor (e.g., "ClassName::method" or "function")
            param_names: List of parameter names to group into object
            class_name: Name of the new parameter object class
        """
        self.target = target
        self.param_names = param_names
        self.class_name = class_name
        # Convert class name to snake_case for parameter name
        self.new_param_name = self._class_name_to_snake_case(class_name)
        # Special case: Config classes use "config" as parameter name
        if class_name.endswith("Config"):
            self.new_param_name = "config"
        self.class_inserted = False

        # Parse target to support class methods like "ClassName::method_name"
        self.target_class_name: Optional[str] = None
        self.target_method_name: Optional[str] = None
        self.is_class_method = "::" in target
        if self.is_class_method:
            parts = target.split("::")
            if len(parts) == 2:
                self.target_class_name = parts[0]
                self.target_method_name = parts[1]
        else:
            self.target_method_name = target

        # Track which class we're currently in
        self.current_class_name: Optional[str] = None

        # Track helper methods found in the target class
        self.helper_methods_to_refactor: set[str] = set()

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and insert the new parameter object class."""
        if self.class_inserted:
            return updated_node

        # Create the new parameter object class
        param_class = self._create_parameter_class()

        # Find insertion point for the new parameter object class
        insertion_index = 0
        target_class_index = None

        for i, stmt in enumerate(updated_node.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                # After imports
                insertion_index = i + 1
            elif isinstance(stmt, cst.ClassDef):
                # If this is the target class, insert before it
                if self.is_class_method and stmt.name.value == self.target_class_name:
                    target_class_index = i
                    break
                # Otherwise, track position after each class
                insertion_index = i + 1

        # If we found the target class, insert before it; otherwise use calculated position
        if target_class_index is not None:
            insertion_index = target_class_index

        # Insert the new class
        new_body = list(updated_node.body)
        new_body.insert(insertion_index, param_class)

        self.class_inserted = True
        return updated_node.with_changes(body=new_body)

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to track current class and pre-compute helper methods."""
        self.current_class_name = node.name.value

        # Pre-compute helper methods if this is the target class
        if self.is_class_method and self.target_class_name == node.name.value:
            self._precompute_helper_methods(node)

        return True

    def _precompute_helper_methods(self, class_def: cst.ClassDef) -> None:
        """Pre-compute which methods are helpers that need refactoring.

        Args:
            class_def: The class definition to analyze
        """
        # Find methods called with consecutive parameters starting from position 0
        # This handles the case where local variables are passed instead of original params
        helper_info = {}
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.target_method_name:
                # Found the target method - now find which methods it calls
                for body_stmt in stmt.body.body if hasattr(stmt.body, "body") else []:
                    if isinstance(body_stmt, cst.SimpleStatementLine):
                        for s in body_stmt.body:
                            if isinstance(s, cst.Return) and isinstance(s.value, cst.Call):
                                # Check if it's a self.method call
                                call = s.value
                                if (
                                    isinstance(call.func, cst.Attribute)
                                    and isinstance(call.func.value, cst.Name)
                                    and call.func.value.value == "self"
                                ):
                                    method_name = call.func.attr.value
                                    # Count consecutive arguments from position 0
                                    # (even if they're not our exact param names, they map positionally)
                                    consecutive_args = 0
                                    for arg in call.args:
                                        if isinstance(arg.value, cst.Name):
                                            consecutive_args += 1
                                        else:
                                            break
                                    # If we have exactly len(param_names) consecutive arguments,
                                    # this is likely a helper method that needs refactoring
                                    if consecutive_args >= len(self.param_names):
                                        helper_info[method_name] = len(self.param_names)
                break

        # Now identify which methods to refactor
        for method_name in helper_info:
            self.helper_methods_to_refactor.add(method_name)

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:  # noqa: N802
        """Leave class definition - find and update helper methods."""
        if self.current_class_name != original_node.name.value:
            self.current_class_name = None
            return updated_node

        # Only for class method targets, update helper methods in the class
        if not self.is_class_method or self.target_class_name != original_node.name.value:
            self.current_class_name = None
            return updated_node

        # Find the target method and see which methods it calls with our params
        target_method = None
        for stmt in original_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.target_method_name:
                target_method = stmt
                break

        if not target_method:
            self.current_class_name = None
            return updated_node

        # Find methods called with consecutive parameters starting from position 0
        # This handles the case where local variables are passed instead of original params
        helper_info = {}
        for stmt in original_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.target_method_name:
                # Found the target method - now find which methods it calls
                for body_stmt in stmt.body.body if hasattr(stmt.body, "body") else []:
                    if isinstance(body_stmt, cst.SimpleStatementLine):
                        for s in body_stmt.body:
                            if isinstance(s, cst.Return) and isinstance(s.value, cst.Call):
                                # Check if it's a self.method call
                                call = s.value
                                if (
                                    isinstance(call.func, cst.Attribute)
                                    and isinstance(call.func.value, cst.Name)
                                    and call.func.value.value == "self"
                                ):
                                    method_name = call.func.attr.value
                                    # Count consecutive arguments from position 0
                                    # (even if they're not our exact param names, they map positionally)
                                    consecutive_args = 0
                                    for arg in call.args:
                                        if isinstance(arg.value, cst.Name):
                                            consecutive_args += 1
                                        else:
                                            break
                                    # If we have exactly len(param_names) consecutive arguments,
                                    # this is likely a helper method that needs refactoring
                                    if consecutive_args >= len(self.param_names):
                                        helper_info[method_name] = len(self.param_names)
                break

        # Now transform the helper methods
        new_body_stmts = []
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value in helper_info:
                # Get the number of parameters to replace in this method
                num_params_to_replace = helper_info[stmt.name.value]
                # Get the parameter names from the helper method (first N params after self)
                method_params = [p.name.value for p in stmt.params.params if p.name.value != "self"]
                # Get the first N parameter names that will be replaced by the config object
                matching_params = method_params[:num_params_to_replace]
                if matching_params:
                    stmt = self._transform_helper_method(stmt, matching_params)
                    # Mark this method for call updates
                    self.helper_methods_to_refactor.add(stmt.name.value)
            new_body_stmts.append(stmt)

        self.current_class_name = None
        if new_body_stmts != list(updated_node.body.body):
            return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body_stmts))
        return updated_node

    def _transform_helper_method(
        self, func_def: cst.FunctionDef, matching_params: list[str]
    ) -> cst.FunctionDef:
        """Transform a helper method to use the parameter object.

        Args:
            func_def: The helper method function definition
            matching_params: The parameter names in this method that should be replaced (e.g., ['start', 'end', 'headers', 'totals'])

        Returns:
            The transformed function definition
        """
        # Replace the matching parameters with the config object
        new_params = []
        replaced = False
        for param in func_def.params.params:
            if param.name.value in matching_params:
                if not replaced:
                    new_params.append(create_parameter(self.new_param_name))
                    replaced = True
                # Skip other matching parameters
            else:
                # Keep non-matching parameters
                new_params.append(param)

        # Update parameters
        func_def = func_def.with_changes(params=func_def.params.with_changes(params=new_params))

        # Update body to reference the config object
        # Map helper method param names to original config field names
        param_mapping = {}
        for i, match_param in enumerate(matching_params):
            if i < len(self.param_names):
                param_mapping[match_param] = self.param_names[i]
        body_visitor = _HelperMethodBodyUpdater(param_mapping, self.new_param_name)
        func_def = func_def.visit(body_visitor)

        return func_def

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and update parameters if it's the target function."""
        # Check if this is the target function
        is_target = False
        if self.is_class_method:
            # For class methods, check both class and method name
            is_target = (
                self.current_class_name == self.target_class_name
                and original_node.name.value == self.target_method_name
            )
        else:
            # For module-level functions, just check method name
            is_target = original_node.name.value == self.target_method_name

        if not is_target:
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

        # Visit the body to update references to parameters and helper method calls
        body_visitor = _ParameterReferenceUpdater(
            self.param_names, self.new_param_name,
            self.helper_methods_to_refactor, len(self.param_names)
        )
        updated_node = updated_node.visit(body_visitor)

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
        # Create __init__ method parameters - use original param names
        init_params = [create_parameter("self")]
        for param_name in self.param_names:
            init_params.append(create_parameter(param_name))

        # Create field assignments for __init__ - use original param names as field names
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


class _HelperMethodBodyUpdater(cst.CSTTransformer):
    """Updates parameter references in helper method bodies to use the config object."""

    def __init__(self, param_mapping: dict[str, str], config_param_name: str) -> None:
        """Initialize the updater.

        Args:
            param_mapping: Maps helper method param names to config object field names
            config_param_name: Name of the config parameter (e.g., 'config')
        """
        self.param_mapping = param_mapping
        self.config_param_name = config_param_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:  # noqa: N802
        """Replace parameter names with config.field references."""
        if updated_node.value in self.param_mapping:
            field_name = self.param_mapping[updated_node.value]
            return cst.Attribute(
                value=cst.Name(self.config_param_name),
                attr=cst.Name(field_name),
            )
        return updated_node


class _FindCalledMethodsVisitor(cst.CSTVisitor):
    """Finds methods called with our target parameters and the argument positions."""

    def __init__(self, param_names: list[str]) -> None:
        """Initialize the visitor.

        Args:
            param_names: Names of parameters we're looking for
        """
        self.param_names = param_names
        self.methods_called: dict[str, set[int]] = {}  # method_name -> set of arg positions

    def visit_Call(self, node: cst.Call) -> bool:  # noqa: N802
        """Find calls to self.method_name with our parameters."""
        if not (
            isinstance(node.func, cst.Attribute)
            and isinstance(node.func.value, cst.Name)
            and node.func.value.value == "self"
        ):
            return True

        method_name = node.func.attr.value
        args = list(node.args)

        # Find positions of arguments that are our parameters
        for i, arg in enumerate(args):
            if isinstance(arg.value, cst.Name) and arg.value.value in self.param_names:
                if method_name not in self.methods_called:
                    self.methods_called[method_name] = set()
                self.methods_called[method_name].add(i)

        return True


class _ParameterReferenceUpdater(cst.CSTTransformer):
    """Updates references to parameters in function bodies to use the parameter object."""

    def __init__(
        self, param_names: list[str], new_param_name: str,
        helper_methods: Optional[set[str]] = None, num_params_to_replace: int = 0
    ) -> None:
        """Initialize the updater.

        Args:
            param_names: Names of parameters to replace
            new_param_name: Name of the new parameter object
            helper_methods: Set of helper method names to update calls for
            num_params_to_replace: Number of leading parameters to replace with config object
        """
        self.param_names = param_names
        self.new_param_name = new_param_name
        self.helper_methods = helper_methods or set()
        self.num_params_to_replace = num_params_to_replace

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:  # noqa: N802
        """Update assignments from parameters to reference the parameter object."""
        # Check if assigning from a parameter
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value in self.param_names:
            # Replace with reference to parameter object field
            return updated_node.with_changes(
                value=cst.Attribute(
                    value=cst.Name(self.new_param_name),
                    attr=cst.Name(updated_node.value.value),
                )
            )
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Update method calls to pass parameter object instead of individual params."""
        # Check if this is a self.method_name call
        if not (
            isinstance(updated_node.func, cst.Attribute)
            and isinstance(updated_node.func.value, cst.Name)
            and updated_node.func.value.value == "self"
        ):
            return updated_node

        method_name = updated_node.func.attr.value
        args = list(updated_node.args)

        # Case 1: Direct parameters
        has_param_arg = any(
            isinstance(arg.value, cst.Name) and arg.value.value in self.param_names
            for arg in args
        )

        if has_param_arg:
            # Build new argument list
            new_args = []
            param_inserted = False
            for arg in args:
                if isinstance(arg.value, cst.Name) and arg.value.value in self.param_names:
                    # Skip parameter arguments; we'll insert the object once
                    if not param_inserted:
                        new_args.append(cst.Arg(value=cst.Name(self.new_param_name)))
                        param_inserted = True
                else:
                    # Keep non-parameter arguments
                    new_args.append(arg)

            return updated_node.with_changes(args=new_args)

        # Case 2: Calls to helper methods that receive N consecutive name arguments
        if method_name in self.helper_methods and len(args) >= self.num_params_to_replace:
            # Check if first N arguments are simple names
            all_names = all(isinstance(args[i].value, cst.Name) for i in range(self.num_params_to_replace))
            if all_names:
                # Replace first N arguments with the config object
                new_args = [cst.Arg(value=cst.Name(self.new_param_name))]
                new_args.extend(args[self.num_params_to_replace:])
                return updated_node.with_changes(args=new_args)

        return updated_node


# Register the command
register_command(IntroduceParameterObjectCommand)
