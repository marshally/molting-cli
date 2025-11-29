"""Replace Conditional with Polymorphism refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


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

        start_line, end_line = self._parse_line_range(line_range)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        wrapper = metadata.MetadataWrapper(module)
        transformer = ReplaceConditionalWithPolymorphismTransformer(
            class_name, method_name, start_line, end_line
        )
        modified_tree = wrapper.visit(transformer)
        self.file_path.write_text(modified_tree.code)

    def _parse_line_range(self, line_range: str) -> tuple[int, int]:
        """Parse line range string into start and end line numbers.

        Args:
            line_range: Line range in format "L2-L5"

        Returns:
            Tuple of (start_line, end_line)

        Raises:
            ValueError: If line range format is invalid
        """
        if not line_range.startswith("L"):
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L2-L5'")

        if "-" not in line_range:
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L2-L5'")

        range_parts = line_range.split("-")
        if len(range_parts) != 2:
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L2-L5'")

        try:
            start_line = int(range_parts[0][1:])
            end_line = int(range_parts[1][1:])
        except ValueError as e:
            raise ValueError(f"Invalid line numbers in '{line_range}': {e}") from e

        return start_line, end_line


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

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track when we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True
            # Extract type constants
            self._extract_type_constants(node)

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

    def _transform_base_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the base class to remove type constants and simplify."""
        new_body: list[cst.BaseStatement] = []
        body = node.body
        if isinstance(body, cst.IndentedBlock):
            for stmt in body.body:
                # Skip type constants
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
                            if target.value in self.type_constants:
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
            # Extract subclass implementations from conditionals
            self._extract_subclasses(original_node)
            # Make base method abstract
            return self._make_abstract_method(updated_node)

        return updated_node

    def _transform_init_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform __init__ to remove type parameter and type-specific parameters."""
        # Simplify parameters to only monthly_salary
        new_params = cst.Parameters(
            params=[
                cst.Param(name=cst.Name("self")),
                cst.Param(name=cst.Name("monthly_salary")),
            ]
        )

        # Simplify body to only assign monthly_salary
        new_body = cst.IndentedBlock(
            body=[
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name("monthly_salary"),
                                    )
                                )
                            ],
                            value=cst.Name("monthly_salary"),
                        )
                    ]
                )
            ]
        )

        return node.with_changes(params=new_params, body=new_body)

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

        for stmt in body.body:
            if isinstance(stmt, cst.If):
                pos = self.get_metadata(metadata.PositionProvider, stmt)
                if pos and pos.start.line == self.start_line:
                    self._process_if_chain(stmt)

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

        # Extract return expression from body
        return_expr = self._extract_return_expression(body)
        if not return_expr:
            return

        # Determine additional parameters needed
        additional_params = self._determine_additional_params(return_expr)

        # Create subclass
        subclass = self._create_subclass(type_name, additional_params, return_expr)
        self.subclasses.append(subclass)

    def _extract_type_name(self, test: cst.BaseExpression) -> str | None:
        """Extract type name from comparison expression."""
        if isinstance(test, cst.Comparison):
            # self.type == self.ENGINEER
            if isinstance(test.comparisons[0].comparator, cst.Attribute):
                attr = test.comparisons[0].comparator
                if isinstance(attr.attr, cst.Name):
                    type_const = attr.attr.value
                    # Map constant name to class name
                    return type_const.capitalize()
        return None

    def _extract_return_expression(self, body: cst.BaseSuite) -> cst.BaseExpression | None:
        """Extract return expression from body."""
        if isinstance(body, cst.IndentedBlock):
            for stmt in body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for s in stmt.body:
                        if isinstance(s, cst.Return):
                            return s.value
        return None

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

    def _uses_attribute(self, expr: cst.BaseExpression, attr_name: str) -> bool:
        """Check if expression uses a specific attribute."""
        collector = AttributeCollector(attr_name)
        expr.visit(collector)
        return collector.found

    def _create_subclass(
        self,
        type_name: str,
        additional_params: list[str],
        return_expr: cst.BaseExpression | None,
    ) -> cst.ClassDef:
        """Create a subclass for a specific type."""
        # Create __init__ method if there are additional parameters
        methods: list[cst.FunctionDef] = []

        if additional_params:
            init_method = self._create_init_method(additional_params)
            methods.append(init_method)

        # Create pay_amount method with proper spacing before it if there's an __init__
        pay_method = self._create_pay_method(return_expr)
        if additional_params:
            # Add blank line before pay_amount
            pay_method = pay_method.with_changes(
                leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))]
            )
        methods.append(pay_method)

        # Create class with proper spacing
        return cst.ClassDef(
            name=cst.Name(type_name),
            bases=[cst.Arg(value=cst.Name("Employee"))],
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

    def _create_pay_method(self, return_expr: cst.BaseExpression | None) -> cst.FunctionDef:
        """Create pay_amount method for subclass."""
        if not return_expr:
            return_expr = cst.Name("None")

        return cst.FunctionDef(
            name=cst.Name("pay_amount"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[cst.SimpleStatementLine(body=[cst.Return(value=return_expr)])]
            ),
        )


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
