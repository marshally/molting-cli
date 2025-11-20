"""Replace Constructor with Factory Function refactoring."""

from pathlib import Path
from rope.base.project import Project
from rope.refactor.introduce_factory import IntroduceFactory
from molting.core.refactoring_base import RefactoringBase


class ReplaceConstructorWithFactoryFunction(RefactoringBase):
    """Replace direct constructor calls with a factory function."""

    def __init__(self, file_path: str, target: str, source_code: str = None):
        """Initialize the ReplaceConstructorWithFactoryFunction refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target class name (e.g., "Employee" or "Employee::__init__")
            source_code: Source code to refactor (optional, will read from file if not provided)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = source_code if source_code is not None else self.file_path.read_text()

        # Parse the target to extract class name
        if "::" in target:
            self.class_name = target.split("::")[0]
        else:
            self.class_name = target

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with factory function
        """
        self.source = source

        # Create a rope project in a temporary location
        project_root = self.file_path.parent
        project = Project(str(project_root))

        try:
            # Get the resource for the file
            resource = project.get_file(self.file_path.name)

            # Get the offset of the class name
            offset = self._get_class_offset()

            # Create introduce factory refactoring
            introduce_factory = IntroduceFactory(project, resource, offset)

            # Generate factory name from class name
            factory_name = f"create_{self.class_name.lower()}"

            # Apply the refactoring (global factory, not static method)
            changes = introduce_factory.get_changes(factory_name, global_factory=True)
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
        # Check that the target class exists in the source
        return f"class {self.class_name}" in source

    def _get_class_offset(self) -> int:
        """Get the offset of the class name in the source code.

        Returns:
            Byte offset of the class name in the source code
        """
        import ast

        try:
            tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class definition
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == self.class_name:
                # Get the offset of the class name
                lines = self.source.split('\n')
                offset = 0
                for i, line in enumerate(lines):
                    if i < node.lineno - 1:
                        offset += len(line) + 1  # +1 for newline
                    else:
                        # Found the line, now find "class ClassName" in it
                        col_offset = line.find(f"class {self.class_name}")
                        if col_offset != -1:
                            # Point to the class name, not the "class" keyword
                            return offset + col_offset + len("class ")
                        break
                raise ValueError(f"Could not find offset for class {self.class_name}")
        raise ValueError(f"Class '{self.class_name}' not found in {self.file_path}")
