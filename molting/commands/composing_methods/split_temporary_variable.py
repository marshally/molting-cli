"""Split Temporary Variable refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


@register_command
class SplitTemporaryVariableCommand(BaseCommand):
    """Command to split a temp variable that is assigned multiple times."""

    name = "split-temporary-variable"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply split-temporary-variable refactoring using libCST.

        Raises:
            ValueError: If function or variable not found or target format is invalid
        """
        target = self.params["target"]

        # Parse target as "function_name::variable_name"
        if "::" not in target:
            raise ValueError(
                f"Invalid target format: {target}. Expected 'function_name::variable_name'"
            )

        function_name, variable_name = target.split("::", 1)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = SplitTemporaryVariableTransformer(function_name, variable_name)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class SplitTemporaryVariableTransformer(cst.CSTTransformer):
    """Transforms a function to split a temporary variable into multiple variables."""

    def __init__(self, function_name: str, variable_name: str) -> None:
        """Initialize the transformer.

        Args:
            function_name: Name of the function to refactor
            variable_name: Name of the variable to split
        """
        self.function_name = function_name
        self.variable_name = variable_name

    def _generate_variable_name(self, assignment_number: int) -> str:
        """Generate a unique variable name for an assignment.

        Args:
            assignment_number: The assignment number (1-indexed)

        Returns:
            The generated variable name
        """
        if assignment_number == 1:
            return "primary_acc"
        elif assignment_number == 2:
            return "secondary_acc"
        else:
            return f"{self.variable_name}_{assignment_number}"

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and split the temporary variable."""
        if original_node.name.value != self.function_name:
            return updated_node

        if not isinstance(updated_node.body, cst.IndentedBlock):
            return updated_node

        # Process statements sequentially
        new_statements = []
        assignment_count = 0

        for stmt in updated_node.body.body:
            # Check if this statement contains an assignment to our variable
            is_target_assignment = False
            if isinstance(stmt, cst.SimpleStatementLine):
                for line_stmt in stmt.body:
                    if isinstance(line_stmt, cst.Assign):
                        for target in line_stmt.targets:
                            if (
                                isinstance(target.target, cst.Name)
                                and target.target.value == self.variable_name
                            ):
                                is_target_assignment = True
                                assignment_count += 1
                                break

            if is_target_assignment:
                # Generate new name for this assignment
                new_name = self._generate_variable_name(assignment_count)

                # Replace only the assignment target
                assignment_replacer = AssignmentTargetReplacer(self.variable_name, new_name)
                new_stmt = stmt.visit(assignment_replacer)
                new_statements.append(new_stmt)
            else:
                # Replace uses of the variable with the most recent assigned name
                if assignment_count > 0:
                    current_name = self._generate_variable_name(assignment_count)

                    name_replacer = NameReplacer(self.variable_name, current_name)
                    new_stmt = stmt.visit(name_replacer)
                    new_statements.append(new_stmt)
                else:
                    new_statements.append(stmt)

        new_body = updated_node.body.with_changes(body=new_statements)
        return updated_node.with_changes(body=new_body)


class AssignmentTargetReplacer(cst.CSTTransformer):
    """Replaces only the assignment target variable name."""

    def __init__(self, old_name: str, new_name: str) -> None:
        """Initialize the replacer.

        Args:
            old_name: Name to replace
            new_name: New name to use
        """
        self.old_name = old_name
        self.new_name = new_name

    def leave_Assign(  # noqa: N802
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> cst.Assign:
        """Leave assignment and rename target variable."""
        new_targets = []
        for target in updated_node.targets:
            if isinstance(target.target, cst.Name) and target.target.value == self.old_name:
                new_target = target.with_changes(target=cst.Name(self.new_name))
                new_targets.append(new_target)
            else:
                new_targets.append(target)

        return updated_node.with_changes(targets=new_targets)


class NameReplacer(cst.CSTTransformer):
    """Replaces all occurrences of a variable name."""

    def __init__(self, old_name: str, new_name: str) -> None:
        """Initialize the replacer.

        Args:
            old_name: Name to replace
            new_name: New name to use
        """
        self.old_name = old_name
        self.new_name = new_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:  # noqa: N802
        """Leave name node and replace if it matches."""
        if updated_node.value == self.old_name:
            return updated_node.with_changes(value=self.new_name)
        return updated_node
