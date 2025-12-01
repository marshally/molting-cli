"""Introduce Foreign Method refactoring command."""

from typing import Any

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_number, parse_target
from molting.core.code_generation_utils import create_parameter
from molting.core.cross_scope_analyzer import CrossScopeAnalyzer
from molting.core.visitors import MethodConflictChecker


class IntroduceForeignMethodCommand(BaseCommand):
    """Introduce Foreign Method refactoring to add functionality to an unmodifiable external class.

    The Introduce Foreign Method refactoring creates a new method in the client class that
    takes an instance of the server class as its first parameter. This pattern is used when
    you need to add behavior to a class that you cannot modify, such as a third-party library
    or framework class.

    **When to use:**
    - You need to add a method to a class but cannot modify it
    - The server class is from an external library or frozen API
    - The functionality is specific to your client context and not appropriate for the
      server class itself
    - You want to avoid duplicating the logic across multiple client classes

    **Example:**
    Before:
        # Cannot modify the Date class, but need to add a next_day() method
        class Employee:
            def calculate_bonus_date(self):
                previous_end = self.period_start
                new_start = previous_end + timedelta(days=1)
                return new_start

    After:
        class Employee:
            def calculate_bonus_date(self):
                previous_end = self.period_start
                new_start = self.next_day(previous_end)
                return new_start

            def next_day(self, arg):
                # Foreign method for Date
                return arg + timedelta(days=1)
    """

    name = "introduce-foreign-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        required = ["target", "for_class", "name"]
        missing = [param for param in required if param not in self.params]
        if missing:
            raise ValueError(
                f"Missing required parameters for introduce-foreign-method: {', '.join(missing)}"
            )

    def execute(self) -> None:
        """Apply introduce-foreign-method refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        for_class = self.params["for_class"]
        method_name = self.params["name"]

        # Parse target: "ClassName::method_name#L<line_number>"
        parts = target.split("#")
        if len(parts) != 2:
            raise ValueError(f"Invalid target format: {target}")

        class_method_part = parts[0]
        line_spec = parts[1]

        # Parse class and method using canonical parser
        try:
            class_name, method_name_to_find = parse_target(class_method_part, expected_parts=2)
        except ValueError as e:
            raise ValueError(f"Invalid class::method format: {class_method_part}") from e

        # Parse line number using canonical parser
        target_line = parse_line_number(line_spec)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Check if the new method name already exists in the class
        conflict_checker = MethodConflictChecker(class_name, method_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Class '{class_name}' already has a method named '{method_name}'")

        # Use CrossScopeAnalyzer to find free variables in the target expression
        analyzer = CrossScopeAnalyzer(module, class_name, method_name_to_find)

        transformer = IntroduceForeignMethodTransformer(
            class_name, method_name_to_find, target_line, for_class, method_name, analyzer
        )

        # Use MetadataWrapper to enable position tracking
        wrapper = MetadataWrapper(module)
        new_module = wrapper.visit(transformer)

        self.file_path.write_text(new_module.code)


class IntroduceForeignMethodTransformer(cst.CSTTransformer):
    """Transforms code by introducing a foreign method."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self,
        class_name: str,
        method_name: str,
        target_line: int,
        for_class: str,
        new_method_name: str,
        analyzer: CrossScopeAnalyzer,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to add the foreign method to
            method_name: Name of the method containing the target line
            target_line: Line number to analyze
            for_class: Name of the external class
            new_method_name: Name of the new foreign method to create
            analyzer: CrossScopeAnalyzer to detect free variables
        """
        self.class_name = class_name
        self.method_name = method_name
        self.target_line = target_line
        self.for_class = for_class
        self.new_method_name = new_method_name
        self.analyzer = analyzer
        self.foreign_method: cst.FunctionDef | None = None
        self.method_found = False
        self.target_expression: cst.BaseExpression | None = None
        self.target_variable: str | None = None
        self.free_variables: list[str] = []
        self.primary_object: str | None = None

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Update imports to add timedelta if importing from datetime."""
        if isinstance(updated_node.module, cst.Name):
            if updated_node.module.value == "datetime":
                # Check if timedelta is already imported
                if isinstance(updated_node.names, cst.ImportStar):
                    return updated_node

                names_list = list(updated_node.names)
                has_timedelta = any(
                    isinstance(name, cst.ImportAlias)
                    and isinstance(name.name, cst.Name)
                    and name.name.value == "timedelta"
                    for name in names_list
                )

                if not has_timedelta:
                    # Add timedelta to imports
                    new_names = names_list + [cst.ImportAlias(name=cst.Name("timedelta"))]
                    return updated_node.with_changes(names=new_names)

        return updated_node

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class to add foreign method."""
        if original_node.name.value == self.class_name:
            return self._process_class(updated_node)
        return updated_node

    def _process_class(self, updated_node: cst.ClassDef) -> cst.ClassDef:
        """Process the class to find the target line and add the foreign method.

        Args:
            updated_node: The updated class definition

        Returns:
            Updated class definition with foreign method added
        """
        # Process each member
        updated_members: list[Any] = []
        for member in updated_node.body.body:
            if isinstance(member, cst.FunctionDef) and member.name.value == self.method_name:
                # Process the method body to replace the line
                processed_method = self._process_method_body(member)
                updated_members.append(processed_method)
            else:
                updated_members.append(member)

        # Add the foreign method if we found and processed the target method
        if self.foreign_method is not None:
            method_with_spacing = self.foreign_method.with_changes(
                leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
            )
            updated_members.append(method_with_spacing)

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=tuple(updated_members))
        )

    def _process_method_body(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Process the method body to replace the target line.

        Args:
            method: The method to process

        Returns:
            Processed method with the replacement
        """
        new_body_stmts: list[Any] = []

        for stmt in method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Get the line number for this statement
                try:
                    pos: Any = self.get_metadata(PositionProvider, stmt)
                    stmt_line = int(pos.start.line)
                except KeyError:
                    stmt_line = -1

                if stmt_line == self.target_line:
                    # This is the target line - extract information and replace it
                    self._extract_target_info(stmt)
                    new_body_stmts.append(self._create_replacement_statement())
                    # Create the foreign method
                    self._create_foreign_method()
                else:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        new_body = method.body.with_changes(body=tuple(new_body_stmts))
        return method.with_changes(body=new_body)

    def _extract_target_info(self, stmt: cst.SimpleStatementLine) -> None:
        """Extract information from the target statement.

        Args:
            stmt: The target statement to analyze
        """
        # Expect an assignment: variable = expression
        if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Assign):
            assign = stmt.body[0]

            # Get the variable name
            if len(assign.targets) == 1:
                target = assign.targets[0].target
                if isinstance(target, cst.Name):
                    self.target_variable = target.value

            # Get the expression
            self.target_expression = assign.value

            # Analyze the expression to find:
            # 1. The primary object (likely of type for_class)
            # 2. Free variables used in the expression
            self.free_variables = self.analyzer.get_free_variables(
                self.target_line, self.target_line
            )

            # Find the primary object - look for Name nodes in the expression
            collector = _NameCollector()
            if self.target_expression:
                self.target_expression.visit(collector)
                # The first name that's NOT in free_variables might be our primary object
                # Or we could heuristically pick the first one
                if collector.names:
                    self.primary_object = collector.names[0]

    def _create_replacement_statement(self) -> cst.SimpleStatementLine:
        """Create the replacement statement with the method call.

        Returns:
            A statement that calls self.method_name(...arguments...)
        """
        # Build the arguments: primary_object, *free_variables
        args = []

        if self.primary_object:
            args.append(cst.Arg(value=cst.Name(self.primary_object)))

        for var in self.free_variables:
            args.append(cst.Arg(value=cst.Name(var)))

        # Create the assignment
        assignment = cst.Assign(
            targets=[cst.AssignTarget(target=cst.Name(self.target_variable or "result"))],
            value=cst.Call(
                func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.new_method_name)),
                args=args,
            ),
        )

        return cst.SimpleStatementLine(body=[assignment])

    def _create_foreign_method(self) -> None:
        """Create the foreign method that wraps the external class operation."""
        if not self.target_expression:
            return

        # Build parameters: self, arg (primary object), *free_variables
        params_list = [create_parameter("self"), create_parameter("arg")]

        for var in self.free_variables:
            params_list.append(create_parameter(var))

        # Create return statement with the original expression
        # We need to replace the primary object reference with 'arg'
        transformed_expr = self._transform_expression_for_foreign_method(self.target_expression)

        return_stmt = cst.Return(value=transformed_expr)

        # Create the method body with comment on the return statement
        return_line = cst.SimpleStatementLine(
            body=[return_stmt],
            leading_lines=[
                cst.EmptyLine(
                    indent=True,
                    whitespace=cst.SimpleWhitespace("    "),
                    comment=cst.Comment(f"# Foreign method for {self.for_class}"),
                )
            ],
        )
        body = cst.IndentedBlock(body=[return_line])

        # Create the method signature
        params = cst.Parameters(params=params_list)

        self.foreign_method = cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=params,
            body=body,
        )

    def _transform_expression_for_foreign_method(
        self, expr: cst.BaseExpression
    ) -> cst.BaseExpression:
        """Transform the expression for use in the foreign method.

        Replaces references to the primary object with 'arg'.

        Args:
            expr: The original expression

        Returns:
            Transformed expression
        """
        replacer = _NameReplacer(self.primary_object or "", "arg")
        return expr.visit(replacer)


class _NameCollector(cst.CSTVisitor):
    """Collects all Name nodes (variable references) in order."""

    def __init__(self) -> None:
        """Initialize the collector."""
        self.names: list[str] = []

    def visit_Name(self, node: cst.Name) -> bool:  # noqa: N802
        """Collect variable names."""
        self.names.append(node.value)
        return True


class _NameReplacer(cst.CSTTransformer):
    """Replaces a specific name with another name."""

    def __init__(self, old_name: str, new_name: str) -> None:
        """Initialize the replacer.

        Args:
            old_name: Name to replace
            new_name: Name to replace with
        """
        self.old_name = old_name
        self.new_name = new_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:  # noqa: N802
        """Replace matching names."""
        if updated_node.value == self.old_name:
            return updated_node.with_changes(value=self.new_name)
        return updated_node


# Register the command
register_command(IntroduceForeignMethodCommand)
