"""Extract Method refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target_with_range
from molting.core.code_generation_utils import create_parameter


class ExtractMethodCommand(BaseCommand):
    """Command to extract a code block into a new method."""

    name = "extract-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply extract-method refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        new_method_name = self.params["name"]

        # Parse target and line range using shared utility
        class_name, method_name, start_line, end_line = parse_target_with_range(target)

        # Read file
        source_code = self.file_path.read_text()

        # First pass: collect line number information
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        line_collector = LineCollector(class_name, method_name, start_line, end_line)
        wrapper.visit(line_collector)

        # Second pass: apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ExtractMethodTransformer(
            class_name,
            method_name,
            new_method_name,
            start_line,
            end_line,
            line_collector.extracted_stmt_indices,
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class LineCollector(cst.CSTVisitor):
    """Collector to determine which statements to extract."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_name: str, method_name: str, start_line: int, end_line: int) -> None:
        """Initialize the collector.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to extract code from
            start_line: Start line number of code to extract (1-indexed)
            end_line: End line number of code to extract (1-indexed)
        """
        self.class_name = class_name
        self.method_name = method_name
        self.start_line = start_line
        self.end_line = end_line
        self.extracted_stmt_indices: list[int] = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to collect line information."""
        if node.name.value != self.method_name:
            return

        for i, stmt in enumerate(node.body.body):
            stmt_lines = self._get_stmt_lines(stmt)  # type: ignore[arg-type]

            if stmt_lines is None:
                continue

            stmt_start, stmt_end = stmt_lines

            # Include if fully contained or if end is in range
            if self.start_line <= stmt_start and stmt_end <= self.end_line:
                # Fully contained
                self.extracted_stmt_indices.append(i)
            elif self.start_line <= stmt_end <= self.end_line:
                # End point is in range
                self.extracted_stmt_indices.append(i)

    def _get_stmt_lines(self, stmt: cst.BaseStatement) -> tuple[int, int] | None:
        """Get the range of lines for a statement including leading lines.

        Args:
            stmt: The statement to get the line range for

        Returns:
            Tuple of (start_line, end_line) inclusive, or None if not available
        """
        try:
            positions = self.get_metadata(metadata.PositionProvider, stmt)
            start = positions.start.line
            end = positions.end.line

            # For SimpleStatementLine, check if there are leading lines with comments
            if isinstance(stmt, cst.SimpleStatementLine):
                if stmt.leading_lines:
                    # Count only the meaningful leading lines (those with comments)
                    leading_count = 0
                    for lead_line in stmt.leading_lines:
                        if lead_line.comment is not None:
                            # This is a line with a comment, count it
                            leading_count += 1
                        elif lead_line.indent:
                            # This is an indented empty line, also count it
                            leading_count += 1
                    start = start - leading_count

            return (start, end)
        except KeyError:
            return None


class ExtractMethodTransformer(cst.CSTTransformer):
    """Transforms a class by extracting a method."""

    def __init__(
        self,
        class_name: str,
        method_name: str,
        new_method_name: str,
        start_line: int,
        end_line: int,
        extracted_stmt_indices: list[int],
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to extract code from
            new_method_name: Name of the new extracted method
            start_line: Start line number of code to extract (1-indexed)
            end_line: End line number of code to extract (1-indexed)
            extracted_stmt_indices: Indices of statements to extract
        """
        self.class_name = class_name
        self.method_name = method_name
        self.new_method_name = new_method_name
        self.start_line = start_line
        self.end_line = end_line
        self.extracted_stmt_indices = extracted_stmt_indices
        self.new_method: cst.FunctionDef | None = None

    def _create_method_call_statement(self) -> cst.SimpleStatementLine:
        """Create a method call statement that invokes the extracted method.

        Returns:
            A SimpleStatementLine containing the method call
        """
        return cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name(self.new_method_name),
                        )
                    )
                )
            ]
        )

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and extract lines if needed."""
        if original_node.name.value != self.method_name:
            return updated_node

        if not self.extracted_stmt_indices:
            return updated_node

        # Collect extracted statements
        extracted_stmts: list[cst.BaseStatement] = []
        new_body: list[cst.BaseStatement] = []

        for i, stmt in enumerate(updated_node.body.body):
            if i in self.extracted_stmt_indices:
                extracted_stmts.append(stmt)  # type: ignore[arg-type]
                # Insert method call at the first extracted statement position
                if len(extracted_stmts) == 1:
                    method_call = self._create_method_call_statement()
                    new_body.append(method_call)
            else:
                new_body.append(stmt)  # type: ignore[arg-type]

        # Create the new extracted method with self parameter
        new_method_body = cst.IndentedBlock(body=tuple(extracted_stmts))
        self.new_method = cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=new_method_body,
        )

        return updated_node.with_changes(body=updated_node.body.with_changes(body=tuple(new_body)))

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and add new method if needed."""
        if original_node.name.value != self.class_name:
            return updated_node

        if self.new_method is not None:
            # Add leading blank line before the new method
            new_method_with_spacing = self.new_method.with_changes(
                leading_lines=[cst.EmptyLine(indent=False, whitespace=cst.SimpleWhitespace(""))]
            )

            # Add the new method to the class
            new_body = tuple(list(updated_node.body.body) + [new_method_with_spacing])
            return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))

        return updated_node


# Register the command
register_command(ExtractMethodCommand)
