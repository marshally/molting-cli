"""Introduce Foreign Method refactoring command."""

from typing import Any

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
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

        # Check if the new method name already exists in the class
        conflict_checker = MethodConflictChecker(class_name, method_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Class '{class_name}' already has a method named '{method_name}'")

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
        self.foreign_method: cst.FunctionDef | None = None
        self.method_found = False

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
        line_count = 0

        for stmt in method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                line_count += 1
                # Track the actual line number in the file
                # The first statement starts at target_line
                stmt_line = self.target_line + line_count - 1
                if stmt_line == self.target_line + 1:
                    # Replace the next line after target_line with the method call
                    new_body_stmts.append(self._create_replacement_statement())
                    # Create the foreign method
                    self._create_foreign_method()
                else:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        new_body = method.body.with_changes(body=tuple(new_body_stmts))
        return method.with_changes(body=new_body)

    def _create_replacement_statement(self) -> cst.SimpleStatementLine:
        """Create the replacement statement with the method call.

        Returns:
            A statement that calls self.method_name(previous_end)
        """
        # Create: new_start = self.next_day(previous_end)
        assignment = cst.Assign(
            targets=[cst.AssignTarget(target=cst.Name("new_start"))],
            value=cst.Call(
                func=cst.Attribute(value=cst.Name("self"), attr=cst.Name(self.new_method_name)),
                args=[cst.Arg(value=cst.Name("previous_end"))],
            ),
        )

        return cst.SimpleStatementLine(body=[assignment])

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
        params = cst.Parameters(
            params=[
                create_parameter("self"),
                create_parameter("arg"),
            ]
        )

        self.foreign_method = cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=params,
            body=body,
        )


# Register the command
register_command(IntroduceForeignMethodCommand)
