"""Replace Conditional with Polymorphism refactoring."""

from pathlib import Path
from typing import List, Optional, Tuple

import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class ReplaceConditionalWithPolymorphism(RefactoringBase):
    """Replace conditional logic with polymorphic method calls."""

    def __init__(self, file_path: str, target: str, type_field: str = "type"):
        """Initialize the ReplaceConditionalWithPolymorphism refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "ClassName::method_name#L13-L20")
            type_field: Name of the field containing the type (default: "type")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.type_field = type_field
        self.source = self.file_path.read_text()

        # Parse the target specification
        try:
            name_part, self.start_line, self.end_line = self.parse_line_range_target(self.target)
        except ValueError:
            raise ValueError(f"Invalid target format: {self.target}")

        # Parse class and method names
        if "::" in name_part:
            self.class_name, self.method_name = self.parse_qualified_target(name_part)
        else:
            raise ValueError(f"Target must be a class method: {self.target}")

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with polymorphic classes
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ReplaceConditionalWithPolymorphismTransformer(
            class_name=self.class_name,
            method_name=self.method_name,
            type_field=self.type_field,
            start_line=self.start_line,
            end_line=self.end_line,
            source_lines=source.split("\n"),
        )
        modified_tree = tree.visit(transformer)

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        return f"class {self.class_name}" in source and f"def {self.method_name}" in source


class ReplaceConditionalWithPolymorphismTransformer(cst.CSTTransformer):
    """Transform CST to replace conditionals with polymorphism."""

    def __init__(
        self,
        class_name: str,
        method_name: str,
        type_field: str,
        start_line: int,
        end_line: int,
        source_lines: list,
    ):
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the conditional method
            method_name: Name of the method with conditional logic
            type_field: Name of the field containing the type
            start_line: Start line of the conditional method
            end_line: End line of the conditional method
            source_lines: Original source code split by lines
        """
        self.class_name = class_name
        self.method_name = method_name
        self.type_field = type_field
        self.start_line = start_line
        self.end_line = end_line
        self.source_lines = source_lines
        self.subclasses: List[cst.ClassDef] = []
        self.inside_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when we enter the target class."""
        if node.name.value == self.class_name:
            self.inside_target_class = True
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process the class definition."""
        if updated_node.name.value == self.class_name:
            self.inside_target_class = False

        return updated_node

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add subclasses to the module."""
        if self.subclasses:
            # Find the main class and add subclasses after it
            new_body = list(updated_node.body)
            # Insert subclasses after the main class
            for i, item in enumerate(new_body):
                if isinstance(item, cst.ClassDef) and item.name.value == self.class_name:
                    # Insert subclasses after the main class
                    for j, subclass in enumerate(self.subclasses):
                        new_body.insert(i + 1 + j, subclass)
                    break

            return updated_node.with_changes(body=new_body)

        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Process function definitions."""
        if updated_node.name.value == self.method_name and self.inside_target_class:
            # This is the target method - extract the conditional logic
            self._extract_conditional_logic(updated_node)

            # Replace the method body with a NotImplementedError
            error_stmt = cst.SimpleStatementLine(
                body=[
                    cst.Raise(
                        exc=cst.Call(
                            func=cst.Name("NotImplementedError"),
                            args=[],
                        )
                    )
                ]
            )
            new_body = cst.IndentedBlock(body=[error_stmt])

            return updated_node.with_changes(body=new_body)

        return updated_node

    def _extract_conditional_logic(self, method_def: cst.FunctionDef) -> None:
        """Extract conditional logic from the method and create subclasses.

        Args:
            method_def: The method definition containing the conditional logic
        """
        # Get the method body
        method_body = method_def.body
        if not isinstance(method_body, cst.IndentedBlock):
            return

        # Find the if statement in the method body
        if_stmt = None
        for stmt in method_body.body:
            if isinstance(stmt, cst.If):
                if_stmt = stmt
                break

        if if_stmt is None:
            return

        # Extract type values and their corresponding code blocks
        type_blocks = self._extract_type_blocks(if_stmt)

        # Create subclasses for each type
        for type_value, block_code in type_blocks:
            if type_value is not None:  # Skip the else block
                subclass = self._create_subclass(type_value, method_def, block_code)
                self.subclasses.append(subclass)

    def _extract_type_blocks(
        self, if_stmt: cst.If
    ) -> List[Tuple[Optional[str], cst.BaseCompoundStatement]]:
        """Extract type values and their corresponding code blocks from an if statement.

        Args:
            if_stmt: The if statement to analyze

        Returns:
            List of (type_value, block_code) tuples
        """
        blocks = []

        # Handle the first condition (if)
        type_value = self._extract_type_value_from_condition(if_stmt.test)
        if type_value:
            block_code = if_stmt.body
            blocks.append((type_value, block_code))

        # Handle elif/else branches
        current_else = if_stmt.orelse
        while current_else:
            if isinstance(current_else, cst.If):
                # This is an elif
                type_value = self._extract_type_value_from_condition(current_else.test)
                if type_value:
                    block_code = current_else.body
                    blocks.append((type_value, block_code))
                current_else = current_else.orelse
            elif isinstance(current_else, cst.Else):
                # This is an else block - we don't create a subclass for this
                current_else = None
            else:
                break

        return blocks

    def _extract_type_value_from_condition(self, condition: cst.BaseExpression) -> Optional[str]:
        """Extract the type value from a comparison condition.

        Args:
            condition: The condition expression

        Returns:
            The type value as a string, or None if extraction fails
        """
        if isinstance(condition, cst.Comparison):
            # Handle: self.type == "engineer"
            for comp in condition.comparisons:
                if isinstance(comp.operator, cst.Equal):
                    if isinstance(comp.comparator, cst.SimpleString):
                        # Remove quotes from the string
                        value = comp.comparator.value
                        return value.strip("'\"")

        return None

    def _create_subclass(
        self, type_value: str, method_def: cst.FunctionDef, block: cst.BaseCompoundStatement
    ) -> cst.ClassDef:
        """Create a subclass for a specific type value.

        Args:
            type_value: The type value for this subclass
            method_def: The original method definition
            block: The code block for this type

        Returns:
            A ClassDef for the subclass
        """
        # Create class name from type value (e.g., "engineer" -> "Engineer")
        class_name = type_value.capitalize()

        # Create the method with the extracted code block
        new_method = method_def.with_changes(body=block)

        # Create the subclass
        subclass = cst.ClassDef(
            name=cst.Name(class_name),
            bases=[cst.Arg(cst.Name(self.class_name))],
            body=cst.IndentedBlock(body=[new_method]),
        )

        return subclass
