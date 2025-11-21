"""Extract Method refactoring - extract a code block into a new method."""

from pathlib import Path
from rope.base.project import Project
from rope.refactor.extract import ExtractMethod as RopeExtractMethod

from molting.core.refactoring_base import RefactoringBase


class ExtractMethod(RefactoringBase):
    """Extract a code block into a new method using rope's extract method refactoring."""

    def __init__(self, file_path: str, target: str, name: str):
        """Initialize the ExtractMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "Order::print_owing#L9-L11")
            name: Name for the new extracted method
        """
        self.file_path = Path(file_path)
        self.target = target
        self.name = name
        self.source = self.file_path.read_text()
        # Parse the target specification to extract line range information.
        # Parses targets like:
        # - "Order::print_owing#L9-L11" -> class/method + line range
        # - "Order::print_owing#L9" -> class/method + single line
        try:
            self.method_spec, self.start_line, self.end_line = self.parse_line_range_target(self.target)
        except ValueError:
            raise ValueError(f"Invalid target format: {self.target}")

    def apply(self, source: str) -> str:
        """Apply the extract method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with extracted method
        """
        # Use the provided source code
        self.source = source

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Calculate byte offsets from line numbers
            # Lines in rope are 1-indexed, so line 9 is at index 8
            lines = source.split('\n')

            # Calculate start offset (beginning of start_line)
            start_offset = 0
            for i in range(self.start_line - 1):
                start_offset += len(lines[i]) + 1  # +1 for newline

            # Calculate end offset (end of end_line)
            end_offset = start_offset
            for i in range(self.start_line - 1, self.end_line):
                end_offset += len(lines[i]) + 1  # +1 for newline

            # Remove the extra newline for the last line
            end_offset -= 1

            # Create extract method refactoring
            extract_refactor = RopeExtractMethod(
                project,
                resource,
                start_offset,
                end_offset
            )

            # Apply the refactoring
            changes = extract_refactor.get_changes(self.name)
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
        # Check that the line numbers are within bounds
        lines = source.split('\n')
        return self.end_line <= len(lines) and self.start_line >= 1
