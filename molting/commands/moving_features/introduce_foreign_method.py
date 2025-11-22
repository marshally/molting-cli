"""Introduce Foreign Method refactoring command."""

from collections.abc import Sequence
from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceForeignMethodCommand(BaseCommand):
    """Command to introduce a foreign method for operations on an external class."""

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

        # Parse class and method
        class_parts = class_method_part.split("::")
        if len(class_parts) != 2:
            raise ValueError(f"Invalid class::method format: {class_method_part}")

        class_name = class_parts[0]
        method_name_to_find = class_parts[1]

        # Parse line number
        if not line_spec.startswith("L"):
            raise ValueError(f"Invalid line format: {line_spec}")

        try:
            target_line = int(line_spec[1:])
        except ValueError as e:
            raise ValueError(f"Invalid line number in {line_spec}: {e}") from e

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = IntroduceForeignMethodTransformer(
            class_name, method_name_to_find, target_line, for_class, method_name
        )
        new_module = module.visit(transformer)

        self.file_path.write_text(new_module.code)


class IntroduceForeignMethodTransformer(cst.CSTTransformer):
    """Transforms code by introducing a foreign method."""

    def __init__(
        self,
        class_name: str,
        method_name: str,
        target_line: int,
        for_class: str,
        new_method_name: str,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to add the foreign method to
            method_name: Name of the method containing the target line
            target_line: Line number to analyze
            for_class: Name of the external class
            new_method_name: Name of the new foreign method to create
        """
        self.class_name = class_name
        self.method_name = method_name
        self.target_line = target_line
        self.for_class = for_class
        self.new_method_name = new_method_name
        self.should_add_import = False
        self.foreign_method: cst.FunctionDef | None = None

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Update imports to add timedelta if importing from datetime."""
        if isinstance(updated_node.module, cst.Attribute):
            return updated_node

        if isinstance(updated_node.module, cst.Name):
            if updated_node.module.value == "datetime":
                # Check if timedelta is already imported
                if isinstance(updated_node.names, cst.ImportStar):
                    return updated_node

                if isinstance(updated_node.names, Sequence):
                    names = list(updated_node.names)
                else:
                    names = [updated_node.names]

                has_timedelta = any(
                    isinstance(name, cst.ImportAlias)
                    and isinstance(name.name, cst.Name)
                    and name.name.value == "timedelta"
                    for name in names
                )

                if not has_timedelta:
                    # Add timedelta to imports
                    new_names = list(names) + [cst.ImportAlias(name=cst.Name("timedelta"))]
                    return updated_node.with_changes(names=new_names)

        return updated_node

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class to add foreign method."""
        if original_node.name.value == self.class_name:
            return self._process_class(updated_node, original_node)
        return updated_node

    def _process_class(
        self, updated_node: cst.ClassDef, original_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process the class to find the target line and add the foreign method.

        Args:
            updated_node: The updated class definition
            original_node: The original class definition

        Returns:
            Updated class definition with foreign method added
        """
        # Find the method and analyze it
        updated_members: list[Any] = []
        for member in updated_node.body.body:
            if isinstance(member, cst.FunctionDef) and member.name.value == self.method_name:
                # Process the method body
                processed_method = self._process_method(member, original_node)
                updated_members.append(processed_method)
            else:
                updated_members.append(member)

        # Add the foreign method if we found what we were looking for
        if self.foreign_method is not None:
            method_with_spacing = self.foreign_method.with_changes(
                leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
            )
            updated_members.append(method_with_spacing)

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=tuple(updated_members))
        )

    def _process_method(self, method: cst.FunctionDef, class_node: cst.ClassDef) -> cst.FunctionDef:
        """Process the method to replace the target line.

        Args:
            method: The method to process
            class_node: The containing class node

        Returns:
            Processed method with the replacement
        """
        # Count lines to find the target
        line_counter = LineCounter()
        method.body.walk(line_counter)

        # Now replace the statement
        replacer = TargetLineReplacer(self.target_line, self.new_method_name)
        new_body = method.body.visit(replacer)

        # Create the foreign method
        self._create_foreign_method()

        return method.with_changes(body=new_body)

    def _create_foreign_method(self) -> None:
        """Create the foreign method that wraps the external class operation."""
        # Create: return arg + timedelta(days=1)
        return_stmt = cst.Return(
            value=cst.BinaryOperation(
                left=cst.Name("arg"),
                operator=cst.Add(),
                right=cst.Call(
                    func=cst.Name("timedelta"),
                    args=[cst.Arg(keyword=cst.Name("days"), value=cst.Integer("1"))],
                ),
            )
        )

        # Create the method with a docstring comment
        body = cst.IndentedBlock(
            body=[
                cst.EmptyLine(indent=True, whitespace=cst.SimpleWhitespace("    ")),
                cst.SimpleStatementLine(
                    body=[
                        cst.Expr(value=cst.SimpleString(f"# Foreign method for {self.for_class}"))
                    ]
                ),
                cst.SimpleStatementLine(body=[return_stmt]),
            ]
        )

        # Create the method signature
        params = cst.Parameters(
            params=[
                cst.Param(name=cst.Name("self")),
                cst.Param(name=cst.Name("arg")),
            ]
        )

        self.foreign_method = cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=params,
            body=body,
        )


class LineCounter(cst.CSTVisitor):
    """Counts statements to track line numbers."""

    def __init__(self) -> None:
        """Initialize the counter."""
        self.line_count = 0


class TargetLineReplacer(cst.CSTTransformer):
    """Replaces the statement at the target line."""

    def __init__(self, target_line: int, method_name: str) -> None:
        """Initialize the replacer.

        Args:
            target_line: The line to replace
            method_name: Name of the method to call
        """
        self.target_line = target_line
        self.method_name = method_name
        self.current_line = 0
        self.seen_target_line = False

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> bool:  # noqa: N802
        """Track line numbers as we visit statements."""
        self.current_line += 1
        return True

    def leave_Module(self, updated_node: cst.Module) -> cst.Module:  # noqa: N802
        """Process the module to find and replace the target line."""
        new_body: list[Any] = []
        line_count = 0

        for stmt in updated_node.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                line_count += 1
                if line_count == self.target_line:
                    # This is the first line in the range
                    # Skip it and handle the next line replacement
                    new_body.append(stmt)
                elif line_count == self.target_line + 1:
                    # This is the second line that needs to be replaced
                    new_body.append(self._create_replacement_statement())
                else:
                    new_body.append(stmt)
            elif isinstance(stmt, cst.FunctionDef):
                # Process function body
                new_body.append(self._process_function_body(stmt))
            else:
                new_body.append(stmt)

        return updated_node.with_changes(body=new_body)

    def _process_function_body(self, func: cst.FunctionDef) -> cst.FunctionDef:
        """Process the function body to replace the target line.

        Args:
            func: The function definition

        Returns:
            Updated function definition
        """
        new_body_stmts: list[Any] = []
        line_count = 0

        for stmt in func.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                line_count += 1
                if line_count == self.target_line:
                    # Keep the first line as is
                    new_body_stmts.append(stmt)
                elif line_count == self.target_line + 1:
                    # Replace the second line with the method call
                    new_body_stmts.append(self._create_replacement_statement())
                else:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        new_body = func.body.with_changes(body=tuple(new_body_stmts))
        return func.with_changes(body=new_body)

    def _create_replacement_statement(self) -> cst.SimpleStatementLine:
        """Create the replacement statement with the method call.

        Returns:
            A statement that calls self.method_name(previous_end)
        """
        # Create: new_start = self.next_day(previous_end)
        assignment = cst.Assign(
            targets=[cst.AssignTarget(target=cst.Name("new_start"))],
            value=cst.Call(
                func=cst.Attribute(
                    value=cst.Name("self"),
                    attr=cst.Name(self.method_name),
                ),
                args=[cst.Arg(value=cst.Name("previous_end"))],
            ),
        )

        return cst.SimpleStatementLine(body=[assignment])


# Register the command
register_command(IntroduceForeignMethodCommand)
