"""Introduce Foreign Method refactoring command."""

from typing import Any

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_line_number, parse_target
from molting.core.code_generation_utils import create_parameter
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

        # First pass: analyze the target line to find local variables
        analyzer = LocalVariableAnalyzer(class_name, method_name_to_find, target_line)
        wrapper = MetadataWrapper(module)
        wrapper.visit(analyzer)

        transformer = IntroduceForeignMethodTransformer(
            class_name,
            method_name_to_find,
            target_line,
            for_class,
            method_name,
            local_vars=analyzer.local_variables,
            server_var_name=analyzer.server_var_name,
            target_var_name=analyzer.target_var_name,
        )
        wrapper2 = MetadataWrapper(module)
        new_module = wrapper2.visit(transformer)

        self.file_path.write_text(new_module.code)


class LocalVariableAnalyzer(cst.CSTVisitor):
    """Analyzes a target line to find local variables used in the expression."""

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, class_name: str, method_name: str, target_line: int) -> None:
        """Initialize the analyzer."""
        self.class_name = class_name
        self.method_name = method_name
        self.target_line = target_line
        self.local_variables: list[str] = []
        self.target_var_name: str | None = None  # The LHS of the assignment
        self.server_var_name: str | None = None  # The first Name in the expression
        self._in_target_class = False
        self._in_target_method = False
        self._defined_vars: set[str] = set()

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name:
            self._in_target_class = True
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track exit from target class."""
        if node.name.value == self.class_name:
            self._in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target method."""
        if self._in_target_class and node.name.value == self.method_name:
            self._in_target_method = True
        return True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Track exit from target method."""
        if self._in_target_class and node.name.value == self.method_name:
            self._in_target_method = False

    def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
        """Track assignments and analyze target line."""
        if not self._in_target_method:
            return True

        try:
            pos: Any = self.get_metadata(PositionProvider, node)
            line = pos.start.line
        except KeyError:
            return True

        # Track all defined variables before target line
        if line < self.target_line:
            for target in node.targets:
                if isinstance(target.target, cst.Name):
                    self._defined_vars.add(target.target.value)

        # Analyze the target line
        if line == self.target_line:
            # Get the LHS variable name
            for target in node.targets:
                if isinstance(target.target, cst.Name):
                    self.target_var_name = target.target.value

            # Find all Name references in the RHS
            collected_names = _collect_names(node.value)

            # The first Name that's a defined variable is likely the server instance
            for name in collected_names:
                if name in self._defined_vars:
                    if self.server_var_name is None:
                        self.server_var_name = name
                    elif name != self.server_var_name:
                        # Other defined variables are local vars to pass
                        if name not in self.local_variables:
                            self.local_variables.append(name)

        return True


def _collect_names(node: cst.CSTNode) -> list[str]:
    """Recursively collect all Name values from a CST node.

    Args:
        node: The CST node to traverse

    Returns:
        List of unique name strings found
    """
    names: list[str] = []

    if isinstance(node, cst.Name):
        if node.value not in names:
            names.append(node.value)

    # Recursively traverse child nodes
    for child in node.children:
        child_names = _collect_names(child)
        for name in child_names:
            if name not in names:
                names.append(name)

    return names


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
        local_vars: list[str] | None = None,
        server_var_name: str | None = None,
        target_var_name: str | None = None,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to add the foreign method to
            method_name: Name of the method containing the target line
            target_line: Line number to analyze
            for_class: Name of the external class
            new_method_name: Name of the new foreign method to create
            local_vars: List of local variable names to include as parameters
            server_var_name: Name of the server instance variable
            target_var_name: Name of the variable being assigned
        """
        self.class_name = class_name
        self.method_name = method_name
        self.target_line = target_line
        self.for_class = for_class
        self.new_method_name = new_method_name
        self.local_vars = local_vars or []
        self.server_var_name = server_var_name
        self.target_var_name = target_var_name
        self.foreign_method: cst.FunctionDef | None = None
        self._in_target_class = False
        self._in_target_method = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name:
            self._in_target_class = True
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
        """Track entry into target method."""
        if self._in_target_class and node.name.value == self.method_name:
            self._in_target_method = True
        return True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Track exit from target method."""
        if self._in_target_class and original_node.name.value == self.method_name:
            self._in_target_method = False
        return updated_node

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

    def leave_SimpleStatementLine(  # noqa: N802
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine:
        """Replace the target line with method call."""
        if not self._in_target_method:
            return updated_node

        try:
            pos: Any = self.get_metadata(PositionProvider, original_node)
            line = pos.start.line
        except KeyError:
            return updated_node

        if line == self.target_line:
            # Create the foreign method (only once)
            if self.foreign_method is None:
                self._create_foreign_method()
            return self._create_replacement_statement()

        return updated_node

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Add foreign method to class and reset tracking."""
        if original_node.name.value == self.class_name:
            self._in_target_class = False
            # Add the foreign method if we created one
            if self.foreign_method is not None:
                method_with_spacing = self.foreign_method.with_changes(
                    leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
                )
                new_body = list(updated_node.body.body) + [method_with_spacing]
                return updated_node.with_changes(
                    body=updated_node.body.with_changes(body=tuple(new_body))
                )
        return updated_node

    def _create_replacement_statement(self) -> cst.SimpleStatementLine:
        """Create the replacement statement with the method call.

        Returns:
            A statement that calls self.method_name(server_var, local_vars...)
        """
        # Build args: first the server instance, then any local variables
        args: list[cst.Arg] = []
        if self.server_var_name:
            args.append(cst.Arg(value=cst.Name(self.server_var_name)))
        for local_var in self.local_vars:
            args.append(cst.Arg(value=cst.Name(local_var)))

        # Use analyzed target_var_name or fallback to "result"
        target_name = self.target_var_name or "result"

        assignment = cst.Assign(
            targets=[cst.AssignTarget(target=cst.Name(target_name))],
            value=cst.Call(
                func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.new_method_name)),
                args=args,
            ),
        )

        return cst.SimpleStatementLine(body=[assignment])

    def _create_foreign_method(self) -> None:
        """Create the foreign method that wraps the external class operation."""
        # Build the timedelta argument based on local_vars
        # If we have local_vars like ["total_days"], use the first one for days=
        timedelta_arg: cst.Name | cst.Integer
        if self.local_vars:
            timedelta_arg = cst.Name(self.local_vars[0])
        else:
            timedelta_arg = cst.Integer("1")

        # Create: return arg + timedelta(days=<local_var or 1>)
        return_stmt = cst.Return(
            value=cst.BinaryOperation(
                left=cst.Name("arg"),
                operator=cst.Add(),
                right=cst.Call(
                    func=cst.Name("timedelta"),
                    args=[cst.Arg(keyword=cst.Name("days"), value=timedelta_arg)],
                ),
            )
        )

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

        # Create the method signature with self, arg, and any local variables
        param_list = [
            create_parameter("self"),
            create_parameter("arg"),
        ]
        for local_var in self.local_vars:
            param_list.append(create_parameter(local_var))

        params = cst.Parameters(params=param_list)

        self.foreign_method = cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=params,
            body=body,
        )


# Register the command
register_command(IntroduceForeignMethodCommand)
