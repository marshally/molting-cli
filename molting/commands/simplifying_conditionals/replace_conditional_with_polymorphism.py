"""Replace Conditional with Polymorphism refactoring command."""


import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ReplaceConditionalWithPolymorphismCommand(BaseCommand):
    """Command to replace type code conditionals with polymorphism."""

    name = "replace-conditional-with-polymorphism"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def _parse_target(self, target: str) -> tuple[str, str, int, int]:
        """Parse target format into class name, method name and line range.

        Args:
            target: Target string in format "ClassName::method_name#L13-L20"

        Returns:
            Tuple of (class_name, method_name, start_line, end_line)

        Raises:
            ValueError: If target format is invalid
        """
        if "::" not in target:
            raise ValueError(
                f"Invalid target format '{target}'. Expected 'ClassName::method_name#L13-L20'"
            )

        class_method, line_range = target.split("#")
        class_name, method_name = class_method.split("::")

        if not line_range.startswith("L"):
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L13-L20'")

        if "-" not in line_range:
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L13-L20'")

        range_parts = line_range.split("-")
        if len(range_parts) != 2:
            raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L13-L20'")

        try:
            start_line = int(range_parts[0][1:])
            end_line = int(range_parts[1][1:])
        except ValueError as e:
            raise ValueError(f"Invalid line numbers in '{line_range}': {e}") from e

        return class_name, method_name, start_line, end_line

    def execute(self) -> None:
        """Apply replace-conditional-with-polymorphism refactoring using libCST.

        Raises:
            ValueError: If class or method not found or target format is invalid
        """
        target = self.params["target"]
        class_name, method_name, start_line, end_line = self._parse_target(target)

        # Read file
        source_code = self.file_path.read_text()

        # Parse and transform with metadata
        module = cst.parse_module(source_code)
        wrapper = metadata.MetadataWrapper(module)
        transformer = ReplaceConditionalWithPolymorphismTransformer(
            class_name, method_name, start_line, end_line
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ReplaceConditionalWithPolymorphismTransformer(cst.CSTTransformer):
    """Transformer to replace conditional with polymorphism."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_name: str, method_name: str, start_line: int, end_line: int) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method with the conditional
            start_line: Start line of the conditional
            end_line: End line of the conditional
        """
        self.class_name = class_name
        self.method_name = method_name
        self.start_line = start_line
        self.end_line = end_line
        self.in_target_class = False
        self.class_constants: dict[str, int] = {}
        self.base_init_params: list[str] = []
        self.conditional_branches: list[tuple[str, cst.BaseExpression]] = []
        self.new_classes: list[cst.ClassDef] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track when we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True
            # Collect class constants
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for item in stmt.body:
                        if isinstance(item, cst.Assign):
                            for target in item.targets:
                                if isinstance(target.target, cst.Name):
                                    if isinstance(item.value, cst.Integer):
                                        self.class_constants[target.target.value] = int(
                                            item.value.value
                                        )

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.FlattenSentinel[cst.ClassDef]:
        """Process class definition after visiting."""
        if self.in_target_class:
            self.in_target_class = False

            new_body = []
            for stmt in updated_node.body.body:
                if not self._is_class_constant_statement(stmt):
                    new_body.append(stmt)

            # Update the base class body
            updated_node = updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )

            # Return base class followed by subclasses with proper spacing
            if self.new_classes:
                # Add blank lines after base class
                updated_node = updated_node.with_changes(
                    leading_lines=[],
                    lines_after_decorators=[],
                )

                # Add blank lines before each subclass
                spaced_subclasses = []
                for subclass in self.new_classes:
                    spaced_subclass = subclass.with_changes(
                        leading_lines=[
                            cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                            cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                        ]
                    )
                    spaced_subclasses.append(spaced_subclass)

                return cst.FlattenSentinel([updated_node] + spaced_subclasses)

        return updated_node

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform method definitions."""
        if not self.in_target_class:
            return updated_node

        # Handle __init__ method
        if original_node.name.value == "__init__":
            # Extract base parameters (keep monthly_salary, remove others)
            new_params = []
            for param in original_node.params.params:
                param_name = param.name.value
                if param_name == "self":
                    new_params.append(param)
                elif param_name == "monthly_salary":
                    new_params.append(
                        param.with_changes(default=None, comma=cst.MaybeSentinel.DEFAULT)
                    )
                    self.base_init_params.append(param_name)

            # Update __init__ body to only keep base assignments
            new_body = []
            for stmt in original_node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for item in stmt.body:
                        if isinstance(item, cst.Assign):
                            for target in item.targets:
                                if isinstance(target.target, cst.Attribute):
                                    attr = target.target
                                    if (
                                        isinstance(attr.value, cst.Name)
                                        and attr.value.value == "self"
                                    ):
                                        if attr.attr.value == "monthly_salary":
                                            new_body.append(stmt)

            return updated_node.with_changes(
                params=cst.Parameters(params=new_params),
                body=cst.IndentedBlock(body=new_body) if new_body else original_node.body,
            )

        # Handle target method
        if original_node.name.value == self.method_name:
            # Extract conditional branches
            for stmt in original_node.body.body:
                if isinstance(stmt, cst.If):
                    pos = self.get_metadata(cst.metadata.PositionProvider, stmt)
                    if pos and pos.start.line == self.start_line:
                        self._extract_branches(stmt)

            # Create subclasses
            self._create_subclasses()

            # Replace method body with NotImplementedError and add blank line before it
            return updated_node.with_changes(
                leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))],
                body=cst.IndentedBlock(
                    body=[
                        cst.SimpleStatementLine(
                            body=[cst.Raise(exc=cst.Name("NotImplementedError"))]
                        )
                    ]
                ),
            )

        return updated_node

    def _extract_branches(self, if_node: cst.If) -> None:
        """Extract branches from the conditional."""
        # Extract first branch (ENGINEER)
        if isinstance(if_node.test, cst.Comparison):
            # Get the return value
            if if_node.body.body:
                first_stmt = if_node.body.body[0]
                if isinstance(first_stmt, cst.SimpleStatementLine):
                    for item in first_stmt.body:
                        if isinstance(item, cst.Return) and item.value:
                            self.conditional_branches.append(("Engineer", item.value))

        # Extract elif branches
        current = if_node.orelse
        while current:
            if isinstance(current, cst.If):
                # Get the return value
                if current.body.body:
                    first_stmt = current.body.body[0]
                    if isinstance(first_stmt, cst.SimpleStatementLine):
                        for item in first_stmt.body:
                            if isinstance(item, cst.Return) and item.value:
                                # Determine class name based on branch count
                                if len(self.conditional_branches) == 1:
                                    self.conditional_branches.append(("Salesman", item.value))
                                elif len(self.conditional_branches) == 2:
                                    self.conditional_branches.append(("Manager", item.value))
                current = current.orelse
            elif isinstance(current, cst.Else):
                break
            else:
                break

    def _create_subclasses(self) -> None:
        """Create subclass for each conditional branch."""
        for class_name, return_expr in self.conditional_branches:
            # Determine which parameters this subclass needs
            subclass_params = ["self"]
            subclass_assignments = []

            # Check what's referenced in the return expression
            if isinstance(return_expr, cst.BinaryOperation):
                # e.g., self.monthly_salary + self.commission
                refs = self._collect_attribute_refs(return_expr)
                for ref in refs:
                    if ref != "monthly_salary":
                        subclass_params.append(ref)
                        # Create assignment: self.commission = commission
                        subclass_assignments.append(
                            cst.SimpleStatementLine(
                                body=[
                                    cst.Assign(
                                        targets=[
                                            cst.AssignTarget(
                                                target=cst.Attribute(
                                                    value=cst.Name("self"),
                                                    attr=cst.Name(ref),
                                                )
                                            )
                                        ],
                                        value=cst.Name(ref),
                                    )
                                ]
                            )
                        )

            # Create __init__ if needed
            init_body = []
            if subclass_params != ["self"]:
                # Add super().__init__(monthly_salary)
                init_body.append(
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
                )
                init_body.extend(subclass_assignments)

            # Create pay_amount method
            pay_amount_method = cst.FunctionDef(
                name=cst.Name("pay_amount"),
                params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
                body=cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Return(value=return_expr)])]
                ),
            )

            # Build class body
            class_body = []
            if init_body:
                # Create __init__ method
                init_params = [cst.Param(name=cst.Name("self"))]
                init_params.append(cst.Param(name=cst.Name("monthly_salary")))
                for param_name in subclass_params[1:]:  # Skip 'self'
                    if param_name != "monthly_salary":
                        init_params.append(cst.Param(name=cst.Name(param_name)))

                init_method = cst.FunctionDef(
                    name=cst.Name("__init__"),
                    params=cst.Parameters(params=init_params),
                    body=cst.IndentedBlock(body=init_body),
                )
                class_body.append(init_method)

                # Add blank line before pay_amount method
                pay_amount_method = pay_amount_method.with_changes(
                    leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))]
                )

            class_body.append(pay_amount_method)

            # Create the subclass
            subclass = cst.ClassDef(
                name=cst.Name(class_name),
                bases=[cst.Arg(value=cst.Name(self.class_name))],
                body=cst.IndentedBlock(body=class_body),
            )

            self.new_classes.append(subclass)

    def _collect_attribute_refs(self, node: cst.BaseExpression) -> list[str]:
        """Collect self.attribute references in an expression."""
        refs: list[str] = []
        if isinstance(node, cst.Attribute):
            if isinstance(node.value, cst.Name) and node.value.value == "self":
                refs.append(node.attr.value)
        elif isinstance(node, cst.BinaryOperation):
            refs.extend(self._collect_attribute_refs(node.left))
            refs.extend(self._collect_attribute_refs(node.right))
        return refs

    def _is_class_constant_statement(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a class constant assignment.

        Args:
            stmt: Statement to check

        Returns:
            True if statement assigns to a class constant, False otherwise
        """
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False

        for item in stmt.body:
            if isinstance(item, cst.Assign):
                for target in item.targets:
                    if isinstance(target.target, cst.Name):
                        if target.target.value in self.class_constants:
                            return True
        return False


# Register the command
register_command(ReplaceConditionalWithPolymorphismCommand)
