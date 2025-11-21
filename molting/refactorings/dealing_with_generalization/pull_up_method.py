"""Pull Up Method refactoring - move a method from subclasses to the superclass."""

import ast
import copy
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class PullUpMethod(RefactoringBase):
    """Move a method from subclasses to the superclass."""

    def __init__(self, file_path: str, target: str, to: str):
        """Initialize the PullUpMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Source method as "ClassName::method_name"
            to: Destination superclass name
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.target = target
        self.superclass_name = to

    def apply(self, source: str) -> str:
        """Apply the pull up method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with method moved to superclass
        """
        # Parse the target class and method name
        class_name, method_name = self.parse_qualified_target(self.target)

        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the superclass and source class
        superclass = self.find_class_def(tree, self.superclass_name)
        if superclass is None:
            raise ValueError(f"Superclass '{self.superclass_name}' not found")

        source_class = self.find_class_def(tree, class_name)
        if source_class is None:
            raise ValueError(f"Source class '{class_name}' not found")

        # Find the method in the source class
        method_node = self.find_method_in_class(source_class, method_name)
        if method_node is None:
            raise ValueError(f"Method '{method_name}' not found in class '{class_name}'")

        # Make a deep copy of the method to add to superclass
        method_copy = copy.deepcopy(method_node)

        # Add the method to the superclass
        superclass.body.append(method_copy)

        # Remove the method from the source class
        source_class.body.remove(method_node)

        # If source class is now empty or only has pass, add a pass statement
        if not source_class.body:
            source_class.body.append(ast.Pass())

        # Fix missing locations for all nodes
        ast.fix_missing_locations(tree)

        # Convert back to source code
        return ast.unparse(tree)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            class_name, method_name = self.parse_qualified_target(self.target)
            tree = ast.parse(source)

            # Check that both superclass and source class exist
            superclass = self.find_class_def(tree, self.superclass_name)
            if superclass is None:
                return False

            source_class = self.find_class_def(tree, class_name)
            if source_class is None:
                return False

            # Check that the method exists in the source class
            method = self.find_method_in_class(source_class, method_name)
            return method is not None

        except (SyntaxError, AttributeError, ValueError):
            return False
