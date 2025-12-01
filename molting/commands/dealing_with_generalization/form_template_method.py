"""Form Template Method refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_class, parse_comma_separated_list, parse_target
from molting.core.code_generation_utils import create_parameter


def parse_steps(steps_str: str) -> dict[str, str]:
    """Parse steps parameter from 'var1:method1,var2:method2' format.

    Args:
        steps_str: Steps string in format 'var1:method1,var2:method2'

    Returns:
        Dictionary mapping variable names to method names

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_steps("base:get_base_amount,tax:get_tax_amount")
        {'base': 'get_base_amount', 'tax': 'get_tax_amount'}
    """
    if not steps_str or not steps_str.strip():
        raise ValueError("Steps parameter cannot be empty")

    steps: dict[str, str] = {}
    pairs = parse_comma_separated_list(steps_str)

    for pair in pairs:
        if ":" not in pair:
            raise ValueError(
                f"Invalid step format '{pair}'. Expected 'variable:method_name' format"
            )

        parts = pair.split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid step format '{pair}'. Expected 'variable:method_name' format"
            )

        var_name = parts[0].strip()
        method_name = parts[1].strip()

        if not var_name or not method_name:
            raise ValueError(
                f"Invalid step format '{pair}'. Variable and method names cannot be empty"
            )

        steps[var_name] = method_name

    return steps


class FormTemplateMethodCommand(BaseCommand):
    """Extract common algorithm structure into a template method.

    The Form Template Method refactoring extracts the common structure of similar
    methods into a superclass method (the template method) and replaces the varying
    parts with abstract method calls that subclasses override. This pattern defines
    the skeleton of an algorithm in a base class, allowing subclasses to override
    specific steps without changing the algorithm's structure.

    **When to use:**
    - You have multiple methods in subclasses with similar structure but different details
    - You want to reduce code duplication while preserving algorithm flexibility
    - You need to ensure subclasses follow the same algorithm structure
    - Different implementations vary only in specific steps of a larger process

    **Parameters:**
    - targets: Comma-separated list of Class::method pairs to analyze
    - name: Name for the template method in the superclass
    - steps: Variable-to-method mappings in format "var1:method1,var2:method2"

    **Usage:**
        molting form-template-method example.py \\
            --targets "ResidentialSite::get_bill_amount,LifelineSite::get_bill_amount" \\
            --name "get_bill_amount" \\
            --steps "base:get_base_amount,tax:get_tax_amount"

    **Example:**

    Before:
        class Site:
            pass

        class ResidentialSite(Site):
            def get_bill_amount(self):
                base = self.units * self.rate
                tax = base * 0.1
                return base + tax

        class LifelineSite(Site):
            def get_bill_amount(self):
                base = self.units * self.rate * 0.5
                tax = base * 0.02
                return base + tax

    After (with steps="base:get_base_amount,tax:get_tax_amount"):
        class Site:
            def get_bill_amount(self):
                base = self.get_base_amount()
                tax = self.get_tax_amount(base)
                return base + tax

            def get_base_amount(self):
                raise NotImplementedError

            def get_tax_amount(self, base):
                raise NotImplementedError

        class ResidentialSite(Site):
            def get_base_amount(self):
                return self.units * self.rate

            def get_tax_amount(self, base):
                return base * 0.1

        class LifelineSite(Site):
            def get_base_amount(self):
                return self.units * self.rate * 0.5

            def get_tax_amount(self, base):
                return base * 0.02
    """

    name = "form-template-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("targets", "name", "steps")

    def execute(self) -> None:
        """Apply form-template-method refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        targets_str = self.params["targets"]
        template_method_name = self.params["name"]
        steps_str = self.params["steps"]

        # Parse targets: "Class1::method,Class2::method"
        target_specs = parse_comma_separated_list(targets_str)
        method_info = []

        for spec in target_specs:
            class_name, method_name = parse_target(spec, expected_parts=2)
            method_info.append((class_name, method_name))

        # Parse steps: "var1:method1,var2:method2"
        steps = parse_steps(steps_str)

        # Read file
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # First pass: identify superclass and collect method implementations
        collector = MethodCollector(method_info)
        module.visit(collector)

        # Second pass: apply transformation
        transformer = FormTemplateMethodTransformer(
            method_info,
            template_method_name,
            collector.superclass_name,
            collector.method_implementations,
            steps,
        )
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class MethodCollector(cst.CSTVisitor):
    """Collects information about methods and their superclass."""

    def __init__(self, method_info: list[tuple[str, str]]) -> None:
        """Initialize the collector.

        Args:
            method_info: List of (class_name, method_name) tuples
        """
        self.method_info = method_info
        self.superclass_name: str | None = None
        self.method_implementations: dict[str, cst.FunctionDef] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to identify superclass and collect methods."""
        class_name = node.name.value

        # Check if this is a subclass (has a base class) - find the superclass
        if node.bases and not self.superclass_name:
            for base in node.bases:
                if isinstance(base.value, cst.Name):
                    self.superclass_name = base.value.value
                    break

        # Collect methods for our target classes
        for target_class, target_method in self.method_info:
            if class_name == target_class:
                method = find_method_in_class(node, target_method)
                if method:
                    self.method_implementations[class_name] = method

        return True


class FormTemplateMethodTransformer(cst.CSTTransformer):
    """Transforms similar methods into a template method pattern."""

    def __init__(
        self,
        method_info: list[tuple[str, str]],
        template_method_name: str,
        superclass_name: str | None,
        method_implementations: dict[str, cst.FunctionDef],
        steps: dict[str, str],
    ) -> None:
        """Initialize the transformer.

        Args:
            method_info: List of (class_name, method_name) tuples
            template_method_name: Name to use for the template method
            superclass_name: Name of the superclass
            method_implementations: Dict of collected method implementations
            steps: Dictionary mapping variable names to method names
        """
        self.method_info = method_info
        self.template_method_name = template_method_name
        self.superclass_name = superclass_name
        self.method_implementations = method_implementations
        self.steps = steps

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and apply transformations."""
        class_name = original_node.name.value

        # Check if this is the superclass
        if self.superclass_name and class_name == self.superclass_name:
            return self._transform_superclass(updated_node)

        # Check if this is one of our target classes
        for target_class, _ in self.method_info:
            if class_name == target_class:
                return self._transform_subclass(updated_node)

        return updated_node

    def _collect_existing_statements(self, node: cst.ClassDef) -> list[cst.BaseStatement]:
        """Collect existing class statements, filtering out 'pass' statements.

        Args:
            node: The class definition node

        Returns:
            List of existing statements except 'pass'
        """
        statements: list[cst.BaseStatement] = []
        for stmt in node.body.body:
            # Skip 'pass' statement
            if isinstance(stmt, cst.SimpleStatementLine):
                has_pass = any(isinstance(item, cst.Pass) for item in stmt.body)
                if has_pass:
                    continue
            statements.append(stmt)  # type: ignore[arg-type]
        return statements

    def _transform_superclass(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the superclass to add the template method and abstract methods."""
        new_body_stmts: list[cst.BaseStatement] = []

        # Add the template method and abstract methods
        new_body_stmts.append(self._create_template_method())
        new_body_stmts.extend(self._create_abstract_methods())

        # Add existing statements
        new_body_stmts.extend(self._collect_existing_statements(node))

        return node.with_changes(body=node.body.with_changes(body=tuple(new_body_stmts)))

    def _transform_subclass(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform a subclass to replace method with abstract method implementations."""
        class_name = node.name.value

        # Find the target method for this class
        target_method_name: str | None = None
        for target_class, target_method in self.method_info:
            if class_name == target_class:
                target_method_name = target_method
                break

        if not target_method_name:
            return node

        new_body_stmts: list[cst.BaseStatement] = []

        target_method_def: cst.FunctionDef | None = (
            find_method_in_class(node, target_method_name) if target_method_name else None
        )

        for stmt in node.body.body:
            # Replace the target method with new abstract method implementations
            if stmt is target_method_def and isinstance(stmt, cst.FunctionDef):
                # Extract the abstract methods from this implementation
                abstract_impls = self._extract_abstract_methods_from_implementation(stmt)
                new_body_stmts.extend(abstract_impls)
            else:
                new_body_stmts.append(stmt)  # type: ignore[arg-type]

        return node.with_changes(body=node.body.with_changes(body=tuple(new_body_stmts)))

    def _analyze_implementation(
        self,
    ) -> tuple[dict[str, list[str]], cst.SimpleStatementLine | None]:
        """Analyze one implementation to understand dependencies and return pattern.

        Returns:
            Tuple of (dependencies_dict, return_statement)
            - dependencies_dict: Maps each step variable to list of variables it depends on
            - return_statement: The return statement (possibly with final calculation), or None
        """
        # Get the first implementation to analyze
        if not self.method_implementations:
            return {}, None

        first_impl = next(iter(self.method_implementations.values()))

        dependencies: dict[str, list[str]] = {}
        var_expressions: dict[str, cst.BaseExpression] = {}
        all_assignments: list[tuple[str, cst.BaseExpression]] = []
        return_value: cst.BaseExpression | None = None

        # Parse the method body
        if isinstance(first_impl.body, cst.IndentedBlock):
            for stmt in first_impl.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for item in stmt.body:
                        if isinstance(item, cst.Assign):
                            # Collect all assignments
                            for target in item.targets:
                                if isinstance(target.target, cst.Name):
                                    var_name = target.target.value
                                    all_assignments.append((var_name, item.value))
                                    if var_name in self.steps:
                                        var_expressions[var_name] = item.value
                        elif isinstance(item, cst.Return) and item.value:
                            return_value = item.value

        # Analyze dependencies for each step variable
        for var_name in self.steps.keys():
            if var_name in var_expressions:
                expr = var_expressions[var_name]
                deps = self._extract_variable_names(expr)
                # Only include dependencies that are step variables or come before this one
                dependencies[var_name] = [d for d in deps if d in self.steps]

        # Analyze return statement
        return_stmt = None
        if return_value:
            # Check if return value is a simple variable or a calculation
            if isinstance(return_value, cst.Name):
                var_name = return_value.value
                # If it's not one of our step variables, look for its assignment
                if var_name not in self.steps:
                    # Find the assignment for this variable
                    for assigned_var, assigned_expr in all_assignments:
                        if assigned_var == var_name:
                            # Create: var_name = expression (on separate line from return)
                            # We'll return this as a marker to add both statements
                            assign_stmt = cst.Assign(
                                targets=[cst.AssignTarget(target=cst.Name(var_name))],
                                value=assigned_expr,
                            )
                            # Return a tuple marker (we'll handle this specially)
                            return_stmt = (assign_stmt, var_name)  # type: ignore[assignment]
                            break
                else:
                    # Just return the step variable
                    return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=return_value)])
            else:
                # Return value is an expression - could be a calculation
                # Just return it directly for now
                return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=return_value)])

        return dependencies, return_stmt

    def _extract_variable_names(self, expr: cst.BaseExpression) -> list[str]:
        """Extract all variable names referenced in an expression.

        Args:
            expr: The expression to analyze

        Returns:
            List of variable names found in the expression
        """
        var_names: list[str] = []

        class NameCollector(cst.CSTVisitor):
            def visit_Name(self, node: cst.Name) -> None:  # noqa: N802
                if not node.value.startswith("self") and node.value != "self":
                    var_names.append(node.value)

        expr.visit(NameCollector())
        return var_names

    def _create_template_method(self) -> cst.FunctionDef:
        """Create the template method using the step mappings.

        Creates a template method that:
        1. Calls each step method in order
        2. Passes only required variables as arguments to later methods
        3. Preserves the original return statement pattern
        """
        body_stmts: list[cst.SimpleStatementLine] = []
        var_names: list[str] = []

        # Analyze one implementation to understand variable dependencies and return pattern
        dependencies, return_expr = self._analyze_implementation()

        # Create assignment statements for each step
        for var_name, method_name in self.steps.items():
            # Determine arguments - pass only variables that this step depends on
            required_vars = dependencies.get(var_name, [])
            args = [cst.Arg(value=cst.Name(v)) for v in required_vars if v in var_names]

            # Create: var_name = self.method_name(args...)
            stmt = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[cst.AssignTarget(target=cst.Name(var_name))],
                        value=cst.Call(
                            func=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(method_name),
                            ),
                            args=args,
                        ),
                    )
                ]
            )
            body_stmts.append(stmt)
            var_names.append(var_name)

        # Add the return statement (either direct or with final calculation)
        if return_expr:
            # Check if it's a tuple (assign + var_name) or a SimpleStatementLine
            if isinstance(return_expr, tuple):
                # Add assignment on one line
                assign_stmt, var_name = return_expr
                body_stmts.append(cst.SimpleStatementLine(body=[assign_stmt]))
                # Add return on next line
                body_stmts.append(
                    cst.SimpleStatementLine(body=[cst.Return(value=cst.Name(var_name))])
                )
            else:
                # It's already a complete statement
                body_stmts.append(return_expr)

        return cst.FunctionDef(
            name=cst.Name(self.template_method_name),
            params=cst.Parameters(
                params=[create_parameter("self")],
            ),
            body=cst.IndentedBlock(body=body_stmts),
        )

    def _create_abstract_methods(self) -> list[cst.FunctionDef]:
        """Create abstract method stubs based on step mappings.

        Creates one abstract method for each step, with parameters for only
        the variables they depend on.
        """
        methods: list[cst.FunctionDef] = []
        var_names: list[str] = []

        # Get dependencies from analysis
        dependencies, _ = self._analyze_implementation()

        for var_name, method_name in self.steps.items():
            # Create parameters: self + only required dependencies
            params = [create_parameter("self")]
            required_vars = dependencies.get(var_name, [])
            params.extend([create_parameter(v) for v in required_vars if v in var_names])

            # Create method: def method_name(self, ...): raise NotImplementedError
            method = cst.FunctionDef(
                name=cst.Name(method_name),
                params=cst.Parameters(params=params),
                body=cst.IndentedBlock(
                    body=[
                        cst.SimpleStatementLine(
                            body=[cst.Raise(exc=cst.Name("NotImplementedError"))]
                        )
                    ]
                ),
            )
            methods.append(method)
            var_names.append(var_name)

        return methods

    def _extract_abstract_methods_from_implementation(
        self, method: cst.FunctionDef
    ) -> list[cst.FunctionDef]:
        """Extract abstract method implementations from a concrete implementation.

        Analyzes the original method to find assignments to variables specified in
        self.steps, and creates methods that return those expressions.

        Args:
            method: The concrete method implementation

        Returns:
            List of extracted abstract method implementations
        """
        methods: list[cst.FunctionDef] = []
        var_expressions: dict[str, cst.BaseExpression] = {}

        # Parse the method body to extract variable assignments
        if isinstance(method.body, cst.IndentedBlock):
            for stmt in method.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for item in stmt.body:
                        if isinstance(item, cst.Assign):
                            # Check if this assigns to one of our step variables
                            for target in item.targets:
                                if isinstance(target.target, cst.Name):
                                    var_name = target.target.value
                                    if var_name in self.steps:
                                        var_expressions[var_name] = item.value

        # Get dependencies from analysis
        dependencies, _ = self._analyze_implementation()

        # Create a method for each step variable, in order
        var_names: list[str] = []
        for var_name, method_name in self.steps.items():
            if var_name in var_expressions:
                # Create parameters: self + only required dependencies
                params = [create_parameter("self")]
                required_vars = dependencies.get(var_name, [])
                params.extend([create_parameter(v) for v in required_vars if v in var_names])

                # Create method that returns the expression
                method_def = cst.FunctionDef(
                    name=cst.Name(method_name),
                    params=cst.Parameters(params=params),
                    body=cst.IndentedBlock(
                        body=[
                            cst.SimpleStatementLine(
                                body=[cst.Return(value=var_expressions[var_name])]
                            )
                        ]
                    ),
                )
                methods.append(method_def)
            var_names.append(var_name)

        return methods


# Register the command
register_command(FormTemplateMethodCommand)
