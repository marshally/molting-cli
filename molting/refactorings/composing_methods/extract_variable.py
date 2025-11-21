"""Extract Variable refactoring - extract an expression into a named variable."""

from pathlib import Path

from rope.base.project import Project
from rope.refactor.extract import ExtractVariable as RopeExtractVariable

from molting.core.refactoring_base import RefactoringBase


class ExtractVariable(RefactoringBase):
    """Extract an expression into a named variable using rope's extract variable refactoring."""

    def __init__(self, file_path: str, target: str, variable_name: str):
        """Initialize the Extract Variable refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "method_name#L10-L12" or "ClassName::method_name#L5-L7")
            variable_name: Name for the extracted variable
        """
        self.file_path = Path(file_path)
        self.target = target
        self.variable_name = variable_name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the extract variable refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with extracted variable
        """
        # Use the provided source code
        self.source = source

        # Write source to file so rope can read it
        self.file_path.write_text(source)

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Parse line range from target
            start_line, end_line = self._parse_line_range(self.target)

            # Get the offset range for the lines
            start_offset, end_offset = self._get_offset_range(start_line, end_line)

            # Create extract variable refactoring
            extract_refactor = RopeExtractVariable(project, resource, start_offset, end_offset)

            # Apply the extract
            changes = extract_refactor.get_changes(self.variable_name)
            project.do(changes)

            # Read the refactored content
            refactored = resource.read()

        finally:
            project.close()

        return refactored

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        # For now, just check that the target exists in the source
        return "#L" in self.target

    def _parse_line_range(self, target: str) -> tuple[int, int]:
        """Parse line range from target specification.

        Handles targets like "method_name#L10-L12" or "ClassName::method_name#L5-L7".

        Args:
            target: Target specification with line range

        Returns:
            Tuple of (start_line, end_line)

        Raises:
            ValueError: If line range format is invalid
        """
        if "#L" not in target:
            raise ValueError(f"Target '{target}' does not contain line range (#L...)")

        # Extract the line range part (everything after #L)
        line_part = target.split("#L")[1]

        if "-" in line_part:
            # Range like 10-L12 or 10-12
            start_str, end_str = line_part.split("-")
            start_line = int(start_str)
            # Handle both "10-L12" and "10-12" formats
            end_str = end_str.lstrip("L")
            end_line = int(end_str)
        else:
            # Single line like 10
            start_line = int(line_part)
            end_line = start_line

        return start_line, end_line

    def _get_offset_range(self, start_line: int, end_line: int) -> tuple[int, int]:
        """Get byte offsets for a line range.

        For extract variable, we extract the expression (right-hand side of assignment).

        Args:
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)

        Returns:
            Tuple of (start_offset, end_offset) in bytes
        """
        lines = self.source.split("\n")

        # Calculate base offset (start of the line)
        base_offset = sum(len(line) + 1 for line in lines[: start_line - 1])

        line = lines[start_line - 1]

        # Find the assignment operator (=) but not ==, !=, <=, >=
        start_pos = 0
        for i, char in enumerate(line):
            if char == "=":
                # Check it's not part of ==, !=, <=, >=
                prev_char = line[i - 1] if i > 0 else " "
                next_char = line[i + 1] if i < len(line) - 1 else " "
                if prev_char not in "=!<>" and next_char != "=":
                    # Found the assignment operator
                    start_pos = i + 1
                    # Skip whitespace after =
                    while start_pos < len(line) and line[start_pos] == " ":
                        start_pos += 1
                    break

        start_offset = base_offset + start_pos
        end_offset = base_offset + len(line)

        return start_offset, end_offset
