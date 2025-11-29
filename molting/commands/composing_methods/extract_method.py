"""Extract Method refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target_with_range
from molting.core.code_generation_utils import create_parameter
from molting.core.visitors import MethodConflictChecker


class ExtractMethodCommand(BaseCommand):
    """Extract a code block into a new method to improve code clarity and reusability.

    The Extract Method refactoring takes a fragment of code within a method and turns it
    into its own new method with a clear, intention-revealing name. This is one of the
    most common and important refactorings, as it helps break down complex methods into
    smaller, more focused pieces of code.

    **When to use:**
    - A method is too long or does multiple things
    - Code within a method is harder to understand than the rest of the code
    - You find similar code in multiple places that could be extracted and reused
    - You want to create a boundary around a conceptual fragment of code
    - A section of code has a clear purpose but complex implementation details

    **Example:**
    Before:
        def print_owing(invoice):
            print_banner()
            # print details
            outstanding = get_outstanding_amount()
            interest_charge = outstanding * 0.12 / 365 * days_overdue
            print(f"name: {invoice.name}")
            print(f"amount: {outstanding}")
            print(f"interest: {interest_charge}")

    After:
        def print_owing(invoice):
            print_banner()
            outstanding = get_outstanding_amount()
            print_details(invoice, outstanding)

        def print_details(invoice, outstanding):
            interest_charge = outstanding * 0.12 / 365 * days_overdue
            print(f"name: {invoice.name}")
            print(f"amount: {outstanding}")
            print(f"interest: {interest_charge}")
    """

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

        # Parse target and line range using canonical functions
        class_name, method_name, start_line, end_line = parse_target_with_range(target)

        # Read file
        source_code = self.file_path.read_text()

        # Check for name conflicts - method should not already exist
        module = cst.parse_module(source_code)
        conflict_checker = MethodConflictChecker(class_name, new_method_name)
        module.visit(conflict_checker)

        if conflict_checker.has_conflict:
            raise ValueError(f"Method '{new_method_name}' already exists in class '{class_name}'")

        # First pass: collect line number information
        wrapper = metadata.MetadataWrapper(module)
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


class VariableUsageAnalyzer(cst.CSTVisitor):
    """Analyzes variable usage in statements to determine what needs to be returned."""

    def __init__(self) -> None:
        """Initialize the analyzer."""
        self.assigned_vars: set[str] = set()
        self.used_vars: set[str] = set()
        self.uninitialized_uses: set[str] = set()
        self.augmented_assigned_vars: set[str] = set()

    def visit_Assign(self, node: cst.Assign) -> None:  # noqa: N802
        """Visit assignment to track assigned variables."""
        for target in node.targets:
            if isinstance(target.target, cst.Name):
                self.assigned_vars.add(target.target.value)

    def visit_Name(self, node: cst.Name) -> None:  # noqa: N802
        """Visit name to track variable usage."""
        # Only track non-builtin names
        self.used_vars.add(node.value)

    def visit_AugAssign(self, node: cst.AugAssign) -> None:  # noqa: N802
        """Visit augmented assignment (e.g., x += 1)."""
        if isinstance(node.target, cst.Name):
            # For augmented assignment, the variable is both used and assigned
            self.used_vars.add(node.target.value)
            self.assigned_vars.add(node.target.value)
            # Track that this variable needs initialization
            self.augmented_assigned_vars.add(node.target.value)

    def analyze_uninitialized(self) -> None:
        """Find variables that are used but not explicitly initialized."""
        self.uninitialized_uses = self.used_vars - self.assigned_vars


class ExtractMethodTransformer(cst.CSTTransformer):
    """Transforms a class by extracting a method."""

    METADATA_DEPENDENCIES = (metadata.ParentNodeProvider,)

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
        self.return_vars: list[str] = []
        self.vars_needing_init: set[str] = set()

    def _create_method_call_statement(self) -> cst.SimpleStatementLine:
        """Create a method call statement that invokes the extracted method.

        Returns:
            A SimpleStatementLine containing the method call
        """
        method_call = cst.Call(
            func=cst.Attribute(
                value=cst.Name("self"),
                attr=cst.Name(self.new_method_name),
            )
        )

        # If there are return variables, assign them
        if self.return_vars:
            if len(self.return_vars) == 1:
                # Single return: var = self.method()
                assignment = cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.return_vars[0]))],
                    value=method_call,
                )
                return cst.SimpleStatementLine(body=[assignment])
            else:
                # Multiple returns: var1, var2 = self.method()
                assignment = cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Tuple(
                                elements=[
                                    cst.Element(value=cst.Name(var)) for var in self.return_vars
                                ]
                            )
                        )
                    ],
                    value=method_call,
                )
                return cst.SimpleStatementLine(body=[assignment])
        else:
            # No return: just call the method
            return cst.SimpleStatementLine(body=[cst.Expr(value=method_call)])

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
        for i, stmt in enumerate(updated_node.body.body):
            if i in self.extracted_stmt_indices:
                extracted_stmts.append(stmt)  # type: ignore[arg-type]

        # Analyze extracted statements BEFORE creating the method call
        # This ensures return_vars is populated for _create_method_call_statement()
        self._analyze_extracted_statements(extracted_stmts, list(updated_node.body.body))

        # Now create the method call with proper return assignment
        new_body: list[cst.BaseStatement] = []
        for i, stmt in enumerate(updated_node.body.body):
            if i in self.extracted_stmt_indices:
                # Insert method call at the first extracted statement position
                if len([j for j in self.extracted_stmt_indices if j <= i]) == 1:
                    method_call = self._create_method_call_statement()
                    new_body.append(method_call)
            else:
                new_body.append(stmt)  # type: ignore[arg-type]

        # Create the new extracted method with self parameter and return statement
        new_method_body = self._create_new_method_body(extracted_stmts)
        self.new_method = cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=new_method_body,
        )

        return updated_node.with_changes(body=updated_node.body.with_changes(body=tuple(new_body)))

    def _analyze_extracted_statements(
        self,
        extracted_stmts: list[cst.BaseStatement],
        all_stmts: list[cst.BaseStatement | cst.BaseSmallStatement],
    ) -> None:
        """Analyze extracted statements to determine what variables need to be returned.

        Args:
            extracted_stmts: Statements being extracted
            all_stmts: All statements in the original method
        """
        # Analyze variable usage in extracted code
        analyzer = VariableUsageAnalyzer()
        for stmt in extracted_stmts:
            stmt.visit(analyzer)

        analyzer.analyze_uninitialized()

        # Track variables that need initialization:
        # Variables that are only augmented assigned (+=, -=, etc.) need initialization
        augmented_only = analyzer.augmented_assigned_vars

        # Determine which variables are assigned in extracted code and used afterwards
        assigned_in_extracted = analyzer.assigned_vars
        next_stmt_idx = max(self.extracted_stmt_indices) + 1

        # Check if assigned variables are used after extraction
        used_after = set()
        if next_stmt_idx < len(all_stmts):
            post_analyzer = VariableUsageAnalyzer()
            for stmt in all_stmts[next_stmt_idx:]:  # type: ignore[assignment]
                stmt.visit(post_analyzer)
            used_after = post_analyzer.used_vars

        # Variables to return are those assigned in extracted code and used after
        potential_returns = assigned_in_extracted & used_after
        self.return_vars = [v for v in potential_returns if v != "self"]

        # Variables needing initialization: returned vars that are augmented-assigned
        self.vars_needing_init = set(self.return_vars) & augmented_only

    def _create_new_method_body(
        self, extracted_stmts: list[cst.BaseStatement]
    ) -> cst.IndentedBlock:
        """Create the body for the new extracted method.

        Args:
            extracted_stmts: Statements to include in the new method

        Returns:
            An IndentedBlock for the new method
        """
        body_stmts: list[cst.BaseStatement] = []

        # Add initializations for returned variables that need it
        # (e.g., only modified with +=, which requires initialization)
        for var in sorted(self.vars_needing_init):  # Sort for deterministic order
            # Initialize with 0 for numeric-looking variables
            init_stmt = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[cst.AssignTarget(target=cst.Name(var))],
                        value=cst.Integer("0"),
                    )
                ]
            )
            body_stmts.append(init_stmt)

        # Add the extracted statements
        body_stmts.extend(extracted_stmts)

        # Add return statement if there are variables to return
        if self.return_vars:
            if len(self.return_vars) == 1:
                # Single return: return var
                return_stmt = cst.SimpleStatementLine(
                    body=[cst.Return(value=cst.Name(self.return_vars[0]))]
                )
            else:
                # Multiple returns: return var1, var2
                return_stmt = cst.SimpleStatementLine(
                    body=[
                        cst.Return(
                            value=cst.Tuple(
                                elements=[
                                    cst.Element(value=cst.Name(var)) for var in self.return_vars
                                ]
                            )
                        )
                    ]
                )
            body_stmts.append(return_stmt)

        return cst.IndentedBlock(body=tuple(body_stmts))

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
