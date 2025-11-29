"""Replace Method with Method Object refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, is_self_attribute, parse_target
from molting.core.code_generation_utils import create_parameter
from molting.core.visitors import ClassConflictChecker


class ReplaceMethodWithMethodObjectCommand(BaseCommand):
    """Replace a long method with a dedicated Method Object class.

    This refactoring extracts a method into its own class, converting local variables
    into instance fields and the original method body into a compute() method. The
    original method then delegates to this new object. This is a key technique from
    Martin Fowler's "Refactoring" that transforms complex local variable scoping into
    an object structure, making it easier to further decompose the method using
    Extract Method.

    **When to use:**
    - When a method has many local variables that make it difficult to extract smaller
      methods
    - When you want to incrementally refactor a long, complex method
    - When local variables represent temporary state that could be better managed as
      object fields
    - As a stepping stone before applying Extract Method to break down long methods

    **Example:**
    Before:
        class Account:
            def calculate_interest(self, years, rate):
                principal = self.balance
                interest = 0
                for year in range(years):
                    interest += principal * rate
                    principal += interest
                return interest

    After:
        class Account:
            def calculate_interest(self, years, rate):
                return CalculateInterest(self, years, rate).compute()

        class CalculateInterest:
            def __init__(self, account, years, rate):
                self.account = account
                self.years = years
                self.rate = rate

            def compute(self):
                principal = self.account.balance
                interest = 0
                for year in range(self.years):
                    interest += principal * self.rate
                    principal += interest
                return interest
    """

    name = "replace-method-with-method-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-method-with-method-object refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target format: "ClassName::method_name"
        class_name, method_name = parse_target(target, expected_parts=2)

        # Read file
        source_code = self.file_path.read_text()

        # Apply transformation in two passes
        module = cst.parse_module(source_code)

        # Generate the method object class name
        method_object_class_name = method_name.capitalize()

        # Check for name conflicts - class name should not already exist
        conflict_checker = ClassConflictChecker(method_object_class_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Class '{method_object_class_name}' already exists in the module")

        # First pass: collect helper methods and method info
        collector = HelperMethodCollector(class_name, method_name)
        module.visit(collector)

        # Second pass: transform
        transformer = ReplaceMethodWithMethodObjectTransformer(
            class_name, method_name, collector.helper_methods
        )
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class HelperMethodCollector(cst.CSTVisitor):
    """Collects helper methods called by the target method."""

    def __init__(self, class_name: str, method_name: str) -> None:
        """Initialize the collector.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to analyze
        """
        self.class_name = class_name
        self.method_name = method_name
        self.helper_methods: dict[str, cst.FunctionDef] = {}
        self.target_method: cst.FunctionDef | None = None
        self.all_class_methods: dict[str, cst.FunctionDef] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to collect all methods."""
        if node.name.value == self.class_name:
            # Collect all methods in the class first
            for stmt in node.body.body:
                if isinstance(stmt, cst.FunctionDef):
                    self.all_class_methods[stmt.name.value] = stmt
                    if stmt.name.value == self.method_name:
                        self.target_method = stmt

            # Now find helper methods called by the target method
            if self.target_method:
                finder = HelperMethodFinder()
                self.target_method.visit(finder)
                for helper_name in finder.helper_methods:
                    if helper_name in self.all_class_methods:
                        self.helper_methods[helper_name] = self.all_class_methods[helper_name]


class HelperMethodFinder(cst.CSTVisitor):
    """Visitor to find helper methods called by the target method."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        self.helper_methods: list[str] = []

    def visit_Call(self, node: cst.Call) -> None:  # noqa: N802
        """Visit call nodes to find helper method calls."""
        if isinstance(node.func, cst.Attribute) and isinstance(node.func.value, cst.Name):
            if node.func.value.value == "self":
                method_name = node.func.attr.value
                if method_name.startswith("_"):
                    self.helper_methods.append(method_name)


class ReplaceMethodWithMethodObjectTransformer(cst.CSTTransformer):
    """Transforms a class by replacing a method with a method object."""

    def __init__(
        self, class_name: str, method_name: str, helper_methods: dict[str, cst.FunctionDef]
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to replace with method object
            helper_methods: Dictionary of helper methods to move to method object
        """
        self.class_name = class_name
        self.method_name = method_name
        self.helper_methods = helper_methods
        self.original_method: cst.FunctionDef | None = None
        self.method_object_class: cst.ClassDef | None = None
        self.in_target_class = False

    def _extract_non_self_params(self, method: cst.FunctionDef) -> list[cst.Param]:
        """Extract all parameters except self from a method.

        Args:
            method: The method to extract parameters from

        Returns:
            List of parameters excluding self
        """
        if not method.params.params:
            return []
        return [p for p in method.params.params if p.name.value != "self"]

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and remove helper methods."""
        if original_node.name.value != self.class_name:
            return updated_node

        self.in_target_class = False

        if self.original_method is None:
            return updated_node

        # Remove helper methods that were moved to the method object
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value not in self.helper_methods:
                    new_body.append(stmt)
            elif isinstance(stmt, cst.BaseStatement):
                new_body.append(stmt)

        return updated_node.with_changes(body=updated_node.body.with_changes(body=tuple(new_body)))

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and capture the method to extract."""
        if not self.in_target_class:
            return updated_node

        if original_node.name.value != self.method_name:
            return updated_node

        # Store the original method for later use
        self.original_method = updated_node

        # Get method parameters (excluding self)
        params = self._extract_non_self_params(updated_node)

        # Create the new method body that delegates to method object
        param_names = [p.name.value for p in params]
        call_args = [cst.Arg(cst.Name("self"))] + [cst.Arg(cst.Name(name)) for name in param_names]

        # Create class name from method name (capitalize first letter)
        method_object_class_name = self.method_name.capitalize()

        new_body = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Call(
                                func=cst.Name(method_object_class_name),
                                args=call_args,
                            ),
                            attr=cst.Name("compute"),
                        )
                    )
                )
            ]
        )

        # Replace method body with delegation
        return updated_node.with_changes(body=cst.IndentedBlock(body=[new_body]))

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and add the method object class after the original class."""
        if self.original_method is None:
            return updated_node

        # Create method object class
        self._create_method_object_class()

        if self.method_object_class is None:
            return updated_node

        # Find the class and insert the method object class after it
        target_class = find_class_in_module(updated_node, self.class_name)
        new_body = []
        for stmt in updated_node.body:
            new_body.append(stmt)
            if stmt is target_class and isinstance(stmt, cst.ClassDef):
                # Add blank lines before the new class
                method_object_with_spacing = self.method_object_class.with_changes(
                    leading_lines=[
                        cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace("")),
                        cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace("")),
                    ]
                )
                new_body.append(method_object_with_spacing)

        return updated_node.with_changes(body=tuple(new_body))

    def _create_method_object_class(self) -> None:
        """Create the method object class from the original method."""
        if self.original_method is None:
            return

        params = self._extract_non_self_params(self.original_method)
        method_object_class_name = self.method_name.capitalize()

        init_method = self._create_init_method(params)
        compute_method = self._create_compute_method()
        transformed_helpers = self._transform_helper_methods()

        class_body = [init_method, compute_method] + transformed_helpers

        self.method_object_class = cst.ClassDef(
            name=cst.Name(method_object_class_name),
            body=cst.IndentedBlock(body=tuple(class_body)),
        )

    def _create_init_method(self, params: list[cst.Param]) -> cst.FunctionDef:
        """Create the __init__ method for the method object class.

        Args:
            params: List of parameters (excluding self) from the original method

        Returns:
            A FunctionDef for the __init__ method
        """
        init_params = [create_parameter("self"), create_parameter("account")] + [
            cst.Param(name=p.name) for p in params
        ]

        init_body = []
        init_body.append(
            cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Name("self"), attr=cst.Name("account")
                                )
                            )
                        ],
                        value=cst.Name("account"),
                    )
                ]
            )
        )
        for p in params:
            init_body.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(value=cst.Name("self"), attr=p.name)
                                )
                            ],
                            value=p.name,
                        )
                    ]
                )
            )

        return cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=init_params),
            body=cst.IndentedBlock(body=tuple(init_body)),
        )

    def _create_compute_method(self) -> cst.FunctionDef:
        """Create the compute method for the method object class.

        Returns:
            A FunctionDef for the compute method
        """
        if self.original_method is None:
            raise ValueError("Original method is None")

        if not isinstance(self.original_method.body, cst.IndentedBlock):
            raise ValueError("Method body is not an IndentedBlock")

        compute_body = self._transform_method_body(self.original_method.body)
        return cst.FunctionDef(
            name=cst.Name("compute"),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=compute_body,
            leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))],
        )

    def _transform_helper_methods(self) -> list[cst.FunctionDef]:
        """Transform helper methods to add spacing.

        Returns:
            List of transformed helper methods
        """
        transformed_helpers = []
        for helper_name, helper_method in self.helper_methods.items():
            transformed_helper = helper_method.with_changes(
                leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
            )
            transformed_helpers.append(transformed_helper)
        return transformed_helpers

    def _transform_method_body(self, body: cst.IndentedBlock) -> cst.IndentedBlock:
        """Transform the method body to use self attributes."""
        if self.original_method is None:
            return body

        # Get parameter names (excluding self)
        params = self._extract_non_self_params(self.original_method)
        param_names = [p.name.value for p in params]

        # Transform body to replace parameter references with self.param
        # and self.method() with self.account.method() for non-helper methods
        transformer = BodyTransformer(param_names, list(self.helper_methods.keys()))
        result = body.visit(transformer)
        if not isinstance(result, cst.IndentedBlock):
            raise ValueError("Transformation did not return an IndentedBlock")
        return result


class BodyTransformer(cst.CSTTransformer):
    """Transforms method body to replace parameter references with self attributes."""

    def __init__(self, param_names: list[str], helper_method_names: list[str]) -> None:
        """Initialize the transformer.

        Args:
            param_names: List of parameter names to replace
            helper_method_names: List of helper method names (don't add account. prefix)
        """
        self.param_names = param_names
        self.helper_method_names = helper_method_names

    def leave_Name(  # noqa: N802
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.Name | cst.Attribute:
        """Transform Name nodes to Attribute nodes for parameters."""
        if updated_node.value in self.param_names:
            return cst.Attribute(value=cst.Name("self"), attr=cst.Name(updated_node.value))
        return updated_node

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Transform self.method() to self.account.method() for non-helper methods."""
        if is_self_attribute(updated_node):
            # Check if this is a method call (not a parameter)
            method_name = updated_node.attr.value
            if method_name not in self.param_names and method_name not in self.helper_method_names:
                # This is a call to a method on the original object
                return cst.Attribute(
                    value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("account")),
                    attr=updated_node.attr,
                )
        return updated_node


# Register the command
register_command(ReplaceMethodWithMethodObjectCommand)
