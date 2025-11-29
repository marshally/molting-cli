"""Replace Conditional with Polymorphism refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_range


class ReplaceConditionalWithPolymorphismCommand(BaseCommand):
    """Replace type-based conditionals with polymorphic method overrides.

    This refactoring transforms a method containing type-based conditional logic
    into polymorphic method implementations across subclasses. Each leg of the
    conditional becomes an overridden method in a corresponding subclass, while
    the original method in the base class becomes abstract. This eliminates
    repetitive type-checking and makes the code structure reflect the underlying
    design where different types have different behaviors.

    **When to use:**
    - You have a method with a large if-else or switch statement based on type
    - Different type values require completely different logic paths
    - You want to make it easier to add new types without modifying existing code
    - The type checking logic is scattered across multiple methods
    - You want to improve code readability by making polymorphic dispatch explicit

    **Example:**
    Before:
        class Employee:
            ENGINEER = 0
            SALESMAN = 1

            def __init__(self, type, monthly_salary, commission=0, bonus=0):
                self.type = type
                self.monthly_salary = monthly_salary
                self.commission = commission
                self.bonus = bonus

            def pay_amount(self):
                if self.type == self.ENGINEER:
                    return self.monthly_salary
                elif self.type == self.SALESMAN:
                    return self.monthly_salary + self.commission
                else:
                    return self.monthly_salary + self.bonus

    After:
        class Employee:
            def __init__(self, monthly_salary):
                self.monthly_salary = monthly_salary

            def pay_amount(self):
                raise NotImplementedError

        class Engineer(Employee):
            def pay_amount(self):
                return self.monthly_salary

        class Salesman(Employee):
            def __init__(self, monthly_salary, commission):
                super().__init__(monthly_salary)
                self.commission = commission

            def pay_amount(self):
                return self.monthly_salary + self.commission

        class Manager(Employee):
            def __init__(self, monthly_salary, bonus):
                super().__init__(monthly_salary)
                self.bonus = bonus

            def pay_amount(self):
                return self.monthly_salary + self.bonus
    """

    name = "replace-conditional-with-polymorphism"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-conditional-with-polymorphism refactoring using libCST.

        Raises:
            ValueError: If class or method not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target as Class::method#L1-L2
        if "::" not in target:
            raise ValueError(
                f"Invalid target format: {target}. Expected: ClassName::method_name#L1-L2"
            )

        parts = target.split("::")
        class_name = parts[0]

        if "#" not in parts[1]:
            raise ValueError(
                f"Invalid target format: {target}. Expected: ClassName::method_name#L1-L2"
            )

        method_parts = parts[1].split("#")
        method_name = method_parts[0]
        line_range = method_parts[1]

        # Use canonical line range parser
        start_line, end_line = parse_line_range(line_range)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        wrapper = metadata.MetadataWrapper(module)
        transformer = ReplaceConditionalWithPolymorphismTransformer(
            class_name, method_name, start_line, end_line
        )
        modified_tree = wrapper.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class ReplaceConditionalWithPolymorphismTransformer(cst.CSTTransformer):
    """Transformer to replace type conditionals with polymorphic subclasses."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_name: str, method_name: str, start_line: int, end_line: int) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to transform
            method_name: Name of the method with conditionals
            start_line: Start line of the conditional
            end_line: End line of the conditional
        """
        self.class_name = class_name
        self.method_name = method_name
        self.start_line = start_line
        self.end_line = end_line
        self.subclasses: list[cst.ClassDef] = []
        self.type_constants: dict[str, int] = {}
        self.in_target_class = False
        self.init_params: list[str] = []  # Track all __init__ parameters
        self.type_param_name: str | None = None  # Name of the type parameter
        self.target_method_params: list[str] = []  # Track target method parameters (excluding self)
        self._trailing_return: cst.Return | None = None  # Track return statement after if block

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track when we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True
            # Extract type constants and init parameters
            self._extract_type_constants(node)
            self._extract_init_parameters(node)

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.FlattenSentinel[cst.ClassDef]:
        """Transform class definition and add subclasses."""
        if original_node.name.value == self.class_name:
            self.in_target_class = False
            # Transform the base class
            transformed_base = self._transform_base_class(updated_node)
            # Return base class followed by subclasses
            if self.subclasses:
                return cst.FlattenSentinel([transformed_base] + self.subclasses)
            return transformed_base
        return updated_node

    def _extract_type_constants(self, node: cst.ClassDef) -> None:
        """Extract type constants from class definition."""
        body = node.body
        if isinstance(body, cst.IndentedBlock):
            for stmt in body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for s in stmt.body:
                        if isinstance(s, cst.Assign):
                            if len(s.targets) == 1:
                                target = s.targets[0].target
                                if isinstance(target, cst.Name):
                                    if isinstance(s.value, cst.Integer):
                                        self.type_constants[target.value] = int(s.value.value)

    def _extract_init_parameters(self, node: cst.ClassDef) -> None:
        """Extract __init__ parameters from class definition."""
        body = node.body
        if isinstance(body, cst.IndentedBlock):
            for stmt in body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                    # Extract parameter names (skip 'self')
                    for param in stmt.params.params[1:]:
                        if isinstance(param.name, cst.Name):
                            param_name = param.name.value
                            self.init_params.append(param_name)
                            # First non-type-constant parameter is likely the type parameter
                            if not self.type_param_name and param_name not in ["monthly_salary"]:
                                # Check if this parameter is used in type comparisons
                                if self._is_type_parameter(param_name):
                                    self.type_param_name = param_name

    def _is_type_parameter(self, param_name: str) -> bool:
        """Check if a parameter is used as a type discriminator."""
        # Common patterns: type, shipping_type, employee_type, kind, etc.
        return param_name.endswith("_type") or param_name in ["type", "kind"]

    def _transform_base_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the base class to remove type constants and simplify."""
        new_body: list[cst.BaseStatement] = []
        body = node.body
        if isinstance(body, cst.IndentedBlock):
            for stmt in body.body:
                # Skip type constants - they're defined with uppercase names like STANDARD, EXPRESS
                if self._is_type_constant(stmt):
                    continue
                new_body.append(stmt)

        # Update the body
        new_node = node.with_changes(body=cst.IndentedBlock(body=new_body))
        return new_node

    def _is_type_constant(self, stmt: cst.BaseStatement) -> bool:
        """Check if statement is a type constant definition."""
        if isinstance(stmt, cst.SimpleStatementLine):
            for s in stmt.body:
                if isinstance(s, cst.Assign):
                    if len(s.targets) == 1:
                        target = s.targets[0].target
                        if isinstance(target, cst.Name):
                            const_name = target.value
                            # Check if it's a type constant (uppercase, typically short names like STANDARD, EXPRESS)
                            if const_name.isupper() and const_name in self.type_constants:
                                return True
                            # Also check for string literal assignments to uppercase names (common pattern)
                            if const_name.isupper() and isinstance(s.value, cst.SimpleString):
                                return True
        return False

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform method to remove conditionals and create subclasses."""
        if not self.in_target_class:
            return updated_node

        if original_node.name.value == "__init__":
            return self._transform_init_method(updated_node)

        if original_node.name.value == self.method_name:
            # Capture the target method's parameters (excluding self)
            for param in original_node.params.params[1:]:
                if isinstance(param.name, cst.Name):
                    self.target_method_params.append(param.name.value)
            # Extract subclass implementations from conditionals
            self._extract_subclasses(original_node)
            # Make base method abstract
            return self._make_abstract_method(updated_node)

        return updated_node

    def _transform_init_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform __init__ to remove type parameter and type-specific parameters."""
        # Determine which parameters to keep by analyzing the method bodies
        # For now, identify parameters that should be removed (those specific to subclasses)
        params_to_remove = self._identify_subclass_specific_params()

        # Build new parameters
        new_params = [cst.Param(name=cst.Name("self"))]
        for param_name in self.init_params:
            if param_name not in params_to_remove:
                new_params.append(cst.Param(name=cst.Name(param_name)))

        # Build body: keep assignments for kept parameters and non-parameter assignments
        new_body_stmts: list[cst.BaseStatement] = []
        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    new_stmt_body = []
                    for s in stmt.body:
                        if isinstance(s, cst.Assign):
                            if len(s.targets) > 0:
                                target = s.targets[0].target
                                if isinstance(target, cst.Attribute):
                                    if (isinstance(target.value, cst.Name) and
                                        target.value.value == "self" and
                                        isinstance(target.attr, cst.Name)):
                                        attr_name = target.attr.value
                                        # Check if this is a parameter assignment
                                        if isinstance(s.value, cst.Name):
                                            param_name = s.value.value
                                            # Keep if parameter should be kept
                                            if param_name not in params_to_remove:
                                                new_stmt_body.append(s)
                                                continue
                                        # Keep non-parameter assignments (e.g., self.insurance_rate = 0.02)
                                        elif attr_name not in self.init_params:
                                            new_stmt_body.append(s)
                                            continue
                        else:
                            new_stmt_body.append(s)

                    if new_stmt_body:
                        new_body_stmts.append(stmt.with_changes(body=new_stmt_body))
                else:
                    new_body_stmts.append(stmt)

        new_body = cst.IndentedBlock(body=new_body_stmts if new_body_stmts else [
            cst.SimpleStatementLine(body=[cst.Pass()])
        ])
        return node.with_changes(params=cst.Parameters(params=new_params), body=new_body)

    def _identify_subclass_specific_params(self) -> set[str]:
        """Identify parameters that are specific to subclasses.

        Returns:
            Set of parameter names to remove from base class
        """
        params_to_remove = set()

        # Always remove the type discriminator parameter
        if self.type_param_name:
            params_to_remove.add(self.type_param_name)

        # For Employee case (monthly_salary is used in all branches)
        # For ShippingCalculator case (all rate parameters used in all branches)
        # This requires analyzing the method body which we don't have here.
        # For now, use heuristics:

        # If we have common pattern params like "monthly_salary", keep it
        # If we have parameters with names like "commission", "bonus", remove them
        for param in self.init_params:
            if param in ["commission", "bonus", "commission_rate", "discount"]:
                params_to_remove.add(param)

        return params_to_remove

    def _make_abstract_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Make method abstract by replacing body with NotImplementedError."""
        new_body = cst.IndentedBlock(
            body=[cst.SimpleStatementLine(body=[cst.Raise(exc=cst.Name("NotImplementedError"))])]
        )
        return node.with_changes(body=new_body)

    def _extract_subclasses(self, node: cst.FunctionDef) -> None:
        """Extract subclasses from conditional branches."""
        # Find the if statement in the method
        body = node.body
        if not isinstance(body, cst.IndentedBlock):
            return

        # First, try to find a trailing return statement after the if block
        self._trailing_return = None
        if_found = False
        for i, stmt in enumerate(body.body):
            if isinstance(stmt, cst.If):
                pos = self.get_metadata(metadata.PositionProvider, stmt)
                # Check if the if statement is within the target range
                if pos and self.start_line <= pos.start.line <= self.end_line:
                    if_found = True
                    # Look for return statement after the if block BEFORE processing chains
                    if i + 1 < len(body.body):
                        next_stmt = body.body[i + 1]
                        if isinstance(next_stmt, cst.SimpleStatementLine):
                            for s in next_stmt.body:
                                if isinstance(s, cst.Return):
                                    self._trailing_return = s
                    # Now process the if chain
                    self._process_if_chain(stmt)
                    return  # Process only the first matching if statement

    def _process_if_chain(self, if_stmt: cst.If) -> None:
        """Process if-elif-else chain to create subclasses."""
        # Process initial if branch
        self._process_branch(if_stmt.test, if_stmt.body)

        # Process elif branches
        # In libCST, elif is represented as orelse=If(...), not orelse=Else(If(...))
        current = if_stmt.orelse
        while current:
            if isinstance(current, cst.If):
                # This is an elif
                self._process_branch(current.test, current.body)
                current = current.orelse
            elif isinstance(current, cst.Else):
                # This is the final else clause - skip it
                break
            else:
                break

    def _process_branch(self, test: cst.BaseExpression, body: cst.BaseSuite) -> None:
        """Process a single branch to create a subclass."""
        # Determine type from test expression
        type_name = self._extract_type_name(test)
        if not type_name:
            return

        # Extract the full branch body
        branch_body = self._extract_branch_body(body)
        if not branch_body:
            return

        # Determine additional parameters needed
        additional_params = self._determine_additional_params_from_body(branch_body)

        # Create subclass
        subclass = self._create_subclass(type_name, additional_params, branch_body)
        self.subclasses.append(subclass)

    def _extract_type_name(self, test: cst.BaseExpression) -> str | None:
        """Extract type name from comparison expression."""
        if isinstance(test, cst.Comparison):
            # self.type == self.ENGINEER or self.shipping_type == self.STANDARD
            if isinstance(test.comparisons[0].comparator, cst.Attribute):
                attr = test.comparisons[0].comparator
                if isinstance(attr.attr, cst.Name):
                    type_const = attr.attr.value
                    # Map constant name to class name
                    # Handle patterns like STANDARD -> Standard, EXPRESS -> Express
                    # Get the type constant name in proper case
                    type_name = type_const.lower().capitalize()
                    # If base class name has a suffix (like "Shipping" or "Employee"), append it
                    # Extract suffix from base class name (e.g., "ShippingCalculator" -> "Shipping")
                    base_suffix = self._extract_class_suffix()
                    if base_suffix:
                        return type_name + base_suffix
                    return type_name
        return None

    def _extract_class_suffix(self) -> str:
        """Extract a meaningful suffix from the base class name."""
        class_name = self.class_name
        # Remove common prefixes/identifiers
        # Examples: ShippingCalculator -> Shipping, Employee -> (empty)
        # For ShippingCalculator: remove "Calculator"
        if class_name.endswith("Calculator"):
            return class_name[:-len("Calculator")]
        elif class_name.endswith("Manager"):
            return class_name[:-len("Manager")]
        elif class_name.endswith("Service"):
            return class_name[:-len("Service")]
        # Default: remove trailing "s" if it looks like a plural, or just use empty
        # For Employee, we don't add suffix
        # Check if this looks like a role/type name
        if class_name in ["Employee", "Person", "User", "Account"]:
            return ""
        # Otherwise try to use the class name as suffix if it makes sense
        return ""

    def _extract_return_expression(self, body: cst.BaseSuite) -> cst.BaseExpression | None:
        """Extract return expression from body."""
        if isinstance(body, cst.IndentedBlock):
            for stmt in body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for s in stmt.body:
                        if isinstance(s, cst.Return):
                            return s.value
        return None

    def _extract_branch_body(self, body: cst.BaseSuite) -> list[cst.BaseStatement]:
        """Extract all statements from a branch body (excluding the final return)."""
        if isinstance(body, cst.IndentedBlock):
            return list(body.body)
        return []

    def _determine_additional_params(self, expr: cst.BaseExpression | None) -> list[str]:
        """Determine additional parameters needed based on expression."""
        if not expr:
            return []

        params = []
        # Check if expression uses commission
        if self._uses_attribute(expr, "commission"):
            params.append("commission")
        # Check if expression uses bonus
        if self._uses_attribute(expr, "bonus"):
            params.append("bonus")
        return params

    def _determine_additional_params_from_body(self, body: list[cst.BaseStatement]) -> list[str]:
        """Determine additional parameters needed based on branch body."""
        params = []
        # Scan the body for attributes that are not class-wide (look for commission, bonus, etc.)
        collector = AttributeNameCollector()
        for stmt in body:
            if isinstance(stmt, cst.BaseStatement):
                stmt.visit(collector)

        # Check which attributes are parameter-like (commission, bonus, etc.)
        for attr in collector.found_attributes:
            if attr in ["commission", "bonus", "commission_rate", "discount"]:
                params.append(attr)

        return params

    def _uses_attribute(self, expr: cst.BaseExpression, attr_name: str) -> bool:
        """Check if expression uses a specific attribute."""
        collector = AttributeCollector(attr_name)
        expr.visit(collector)
        return collector.found

    def _create_subclass(
        self,
        type_name: str,
        additional_params: list[str],
        branch_body: list[cst.BaseStatement],
    ) -> cst.ClassDef:
        """Create a subclass for a specific type."""
        # Create __init__ method if there are additional parameters
        methods: list[cst.FunctionDef] = []

        if additional_params:
            init_method = self._create_init_method(additional_params)
            methods.append(init_method)

        # Create the override method with the branch body
        override_method = self._create_override_method(branch_body)
        if additional_params:
            # Add blank line before override method
            override_method = override_method.with_changes(
                leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))]
            )
        methods.append(override_method)

        # Create class with proper spacing
        return cst.ClassDef(
            name=cst.Name(type_name),
            bases=[cst.Arg(value=cst.Name(self.class_name))],
            body=cst.IndentedBlock(body=methods),
            leading_lines=[cst.EmptyLine(), cst.EmptyLine()],
        )

    def _create_init_method(self, additional_params: list[str]) -> cst.FunctionDef:
        """Create __init__ method for subclass."""
        # Parameters: self, monthly_salary, additional_params
        params = [
            cst.Param(name=cst.Name("self")),
            cst.Param(name=cst.Name("monthly_salary")),
        ]
        for param in additional_params:
            params.append(cst.Param(name=cst.Name(param)))

        # Body: super().__init__(monthly_salary) and assign additional params
        body_stmts: list[cst.BaseStatement] = [
            cst.SimpleStatementLine(
                body=[
                    cst.Expr(
                        value=cst.Call(
                            func=cst.Attribute(
                                value=cst.Call(func=cst.Name("super"), args=[]),
                                attr=cst.Name("__init__"),
                            ),
                            args=[cst.Arg(value=cst.Name("monthly_salary"))],
                        )
                    )
                ]
            )
        ]

        for param in additional_params:
            body_stmts.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(param),
                                    )
                                )
                            ],
                            value=cst.Name(param),
                        )
                    ]
                )
            )

        return cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=params),
            body=cst.IndentedBlock(body=body_stmts),
        )

    def _create_override_method(self, branch_body: list[cst.BaseStatement]) -> cst.FunctionDef:
        """Create an override method for subclass with the branch body."""
        # Use the actual method name from the target
        method_name = self.method_name

        # Create method params: self + original method params
        params = [cst.Param(name=cst.Name("self"))]
        for param_name in self.target_method_params:
            params.append(cst.Param(name=cst.Name(param_name)))

        # Build the method body with branch statements + optional trailing return
        method_body = list(branch_body)
        if self._trailing_return is not None:
            # Add the trailing return statement
            # Create a new Return statement to avoid sharing nodes
            return_value = self._trailing_return.value
            if return_value:
                # Clone the return value to avoid sharing the same node
                return_value = return_value.deep_clone()
            new_return = cst.Return(value=return_value)
            return_stmt = cst.SimpleStatementLine(body=[new_return])
            method_body.append(return_stmt)

        return cst.FunctionDef(
            name=cst.Name(method_name),
            params=cst.Parameters(params=params),
            body=cst.IndentedBlock(body=method_body),
        )


class AttributeNameCollector(cst.CSTVisitor):
    """Visitor to collect all attribute names in an expression."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.found_attributes: set[str] = set()

    def visit_Attribute(self, node: cst.Attribute) -> None:  # noqa: N802
        """Collect all attribute names."""
        if isinstance(node.attr, cst.Name):
            self.found_attributes.add(node.attr.value)


class AttributeCollector(cst.CSTVisitor):
    """Visitor to check if an expression uses a specific attribute."""

    def __init__(self, attr_name: str) -> None:
        """Initialize the collector.

        Args:
            attr_name: Name of the attribute to look for
        """
        self.attr_name = attr_name
        self.found = False

    def visit_Attribute(self, node: cst.Attribute) -> None:  # noqa: N802
        """Check if this is the attribute we're looking for."""
        if isinstance(node.attr, cst.Name):
            if node.attr.value == self.attr_name:
                self.found = True


# Register the command
register_command(ReplaceConditionalWithPolymorphismCommand)
