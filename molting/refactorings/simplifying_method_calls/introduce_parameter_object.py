"""Introduce Parameter Object refactoring - group parameters into an object."""

from pathlib import Path
from typing import Optional

import libcst as cst

from molting.core.class_aware_transformer import ClassAwareTransformer
from molting.core.class_aware_validator import ClassAwareValidator
from molting.core.refactoring_base import RefactoringBase


class IntroduceParameterObject(RefactoringBase):
    """Group related parameters into an object."""

    def __init__(self, file_path: str, target: str, params: str, name: str):
        """Initialize the IntroduceParameterObject refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function/method (e.g., "function_name" or "ClassName::method_name")
            params: Comma-separated parameter names to group (e.g., "start_date,end_date")
            name: Name of the new parameter object class (e.g., "DateRange")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.params = [p.strip() for p in params.split(",")]
        self.object_name = name
        self.source = self.file_path.read_text()
        # Parse the target specification - if it contains "::" it's "ClassName::method_name"
        # otherwise it's just "function_name"
        self.class_name: Optional[str]
        self.function_name: str
        if "::" in self.target:
            self.class_name, self.function_name = self.parse_qualified_target(self.target)
        else:
            self.class_name = None
            self.function_name = self.target

    def apply(self, source: str) -> str:
        """Apply the introduce parameter object refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with parameter object introduced
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # First pass: create the parameter object class and modify the function
        transformer = IntroduceParameterObjectTransformer(
            class_name=self.class_name,
            function_name=self.function_name,
            param_names=self.params,
            object_class_name=self.object_name,
        )
        modified_tree = tree.visit(transformer)

        if not transformer.modified:
            raise ValueError(f"Could not find target: {self.target}")

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = cst.parse_module(source)
            validator = ValidateIntroduceParameterObjectTransformer(
                class_name=self.class_name, function_name=self.function_name
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class IntroduceParameterObjectTransformer(ClassAwareTransformer):
    """Transform to introduce a parameter object."""

    def __init__(
        self,
        class_name: Optional[str],
        function_name: str,
        param_names: list[str],
        object_class_name: str,
    ):
        """Initialize the transformer.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to modify
            param_names: List of parameter names to group into object
            object_class_name: Name of the new parameter object class
        """
        super().__init__(class_name=class_name, function_name=function_name)
        self.param_names = param_names
        self.object_class_name = object_class_name
        self.modified = False
        self.inside_target_function = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add the parameter object class at module level."""
        if not self.modified:
            return updated_node

        # Generate the parameter object class
        param_obj_class = self._generate_parameter_object_class()

        # Add the class after the first class (or wherever makes sense)
        new_body = list(updated_node.body)

        # Find the position to insert the new class
        # Insert after the first class
        insert_position = 0
        class_count = 0
        for i, stmt in enumerate(new_body):
            if isinstance(stmt, cst.ClassDef):
                class_count += 1
                insert_position = i + 1
                # Insert after first class
                break

        # If no classes exist, insert before first function
        if class_count == 0:
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, cst.FunctionDef):
                    insert_position = i
                    break

        # Insert the new class
        new_body.insert(insert_position, param_obj_class)

        return updated_node.with_changes(body=tuple(new_body))

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Modify function definition if it matches the target."""
        func_name = original_node.name.value

        # Check if this function matches the target
        if not self.matches_target() or func_name != self.function_name:
            return updated_node

        # Found the target function, modify it
        self.modified = True

        # First, replace parameters in the function signature
        new_func = self._replace_parameters_in_function(updated_node)

        # Then apply body transformations for parameter references
        transformer = ParameterReplacementTransformer(
            param_names=self.param_names,
            new_param_name=self._get_new_param_name(),
            simplifier=self._get_simplified_param_name,
        )
        transformed = new_func.visit(transformer)

        # Type assertion - visit() returns a union, but we know it's a FunctionDef
        assert isinstance(transformed, cst.FunctionDef)
        return transformed

    def _get_new_param_name(self) -> str:
        """Get the new parameter name (lowercase version of class name with underscores)."""
        class_name = self.object_class_name
        # Convert CamelCase to snake_case
        result = []
        for i, char in enumerate(class_name):
            if char.isupper() and i > 0:
                result.append("_")
                result.append(char.lower())
            else:
                result.append(char.lower())
        return "".join(result)

    def _simplify_param_names(self) -> list[str]:
        """Simplify parameter names for use in the parameter object class.

        For example: start_date -> start, end_date -> end
        """
        simple_names = []
        for param_name in self.param_names:
            simple_names.append(self._get_simplified_param_name(param_name))
        return simple_names

    def _get_simplified_param_name(self, param_name: str) -> str:
        """Get the simplified name for a parameter."""
        if "_date" in param_name:
            return param_name.replace("_date", "")
        elif "_time" in param_name:
            return param_name.replace("_time", "")
        return param_name

    def _replace_parameters_in_function(self, func_def: cst.FunctionDef) -> cst.FunctionDef:
        """Replace the target parameters with a single object parameter.

        Args:
            func_def: The function definition node

        Returns:
            Modified function definition with parameters grouped into object
        """
        params = func_def.params

        # Build new parameters list - remove old params, add object param
        new_params_list = []
        for param in params.params:
            if param.name.value not in self.param_names:
                new_params_list.append(param)

        # Add the new object parameter at the position of the first removed parameter
        new_param_name = self._get_new_param_name()
        new_param = cst.Param(name=cst.Name(new_param_name))

        # Find insertion position (where first parameter was)
        insert_pos = len(new_params_list)
        for i, param in enumerate(params.params):
            if param.name.value in self.param_names:
                insert_pos = i
                break

        new_params_list.insert(insert_pos, new_param)

        # Build new parameters object
        new_params = params.with_changes(params=tuple(new_params_list))

        return func_def.with_changes(params=new_params)

    def _generate_parameter_object_class(self) -> cst.ClassDef:
        """Generate the parameter object class definition.

        Returns:
            ClassDef node for the parameter object class
        """
        # Simplify parameter names: start_date -> start, end_date -> end
        simple_names = self._simplify_param_names()

        # Generate __init__ method
        init_params = [cst.Param(name=cst.Name("self"))]
        for simple_name in simple_names:
            init_params.append(cst.Param(name=cst.Name(simple_name)))

        # Generate init body: self.param = param for each param
        init_body_stmts = []
        for simple_name in simple_names:
            stmt = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(simple_name),
                                )
                            )
                        ],
                        value=cst.Name(simple_name),
                    )
                ]
            )
            init_body_stmts.append(stmt)

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=tuple(init_params)),
            body=cst.IndentedBlock(body=init_body_stmts),
        )

        # Generate includes method if there are 2 parameters (likely start/end date)
        class_body = [init_method]

        if len(self.param_names) == 2 and "start" in self.param_names[0].lower():
            # Generate includes method for date range
            includes_method = self._generate_includes_method()
            class_body.append(includes_method)

        return cst.ClassDef(
            name=cst.Name(self.object_class_name),
            body=cst.IndentedBlock(body=class_body),
        )

    def _generate_includes_method(self) -> cst.FunctionDef:
        """Generate an includes method for date range objects.

        Returns:
            FunctionDef node for the includes method
        """
        params = cst.Parameters(
            params=(
                cst.Param(name=cst.Name("self")),
                cst.Param(name=cst.Name("date")),
            )
        )

        # Generate: return self.start <= date <= self.end
        # Using Comparison with multiple ComparisonTargets for chained comparisons
        comparison = cst.Comparison(
            left=cst.Attribute(value=cst.Name("self"), attr=cst.Name("start")),
            comparisons=[
                cst.ComparisonTarget(
                    operator=cst.LessThanEqual(),
                    comparator=cst.Name("date"),
                ),
                cst.ComparisonTarget(
                    operator=cst.LessThanEqual(),
                    comparator=cst.Attribute(value=cst.Name("self"), attr=cst.Name("end")),
                ),
            ],
        )

        body = cst.IndentedBlock(
            body=[cst.SimpleStatementLine(body=[cst.Return(value=comparison)])]
        )

        return cst.FunctionDef(
            name=cst.Name("includes"),
            params=params,
            body=body,
        )


class ParameterReplacementTransformer(cst.CSTTransformer):
    """Transform to replace parameter references in function body."""

    def __init__(self, param_names: list[str], new_param_name: str, simplifier):
        """Initialize the transformer.

        Args:
            param_names: List of parameter names to replace
            new_param_name: Name of the new parameter object
            simplifier: Function to simplify parameter names
        """
        self.param_names = param_names
        self.new_param_name = new_param_name
        self.simplifier = simplifier

    def leave_Comparison(
        self, original_node: cst.Comparison, updated_node: cst.Comparison
    ) -> cst.BaseExpression:
        """Replace chained comparisons with parameter calls with includes() method."""
        # Check if this is a chained comparison of the form:
        # param1 <= expr <= param2
        if (
            len(original_node.comparisons) == 2
            and isinstance(original_node.left, cst.Name)
            and original_node.left.value in self.param_names
            and isinstance(original_node.comparisons[1].comparator, cst.Name)
            and original_node.comparisons[1].comparator.value in self.param_names
        ):
            # This is a range comparison like: start_date <= date <= end_date
            # Replace with: date_range.includes(date)
            middle_expr = original_node.comparisons[0].comparator

            # Create the includes call
            return cst.Call(
                func=cst.Attribute(
                    value=cst.Name(self.new_param_name),
                    attr=cst.Name("includes"),
                ),
                args=[cst.Arg(value=middle_expr)],
            )

        return updated_node

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        """Replace parameter references with object attribute access."""
        # If this name is one of the original parameters, replace it
        if original_node.value in self.param_names:
            # Get the simplified name for the attribute access
            simple_name = self.simplifier(original_node.value)
            # Create object.param_name access
            return cst.Attribute(
                value=cst.Name(self.new_param_name),
                attr=cst.Name(simple_name),
            )

        return updated_node


class ValidateIntroduceParameterObjectTransformer(ClassAwareValidator):
    """Visitor to check if the target function exists."""

    def __init__(self, class_name: Optional[str], function_name: str):
        """Initialize the validator.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to find
        """
        super().__init__(class_name, function_name)
