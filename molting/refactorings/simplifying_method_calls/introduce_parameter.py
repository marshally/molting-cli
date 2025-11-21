"""Introduce Parameter refactoring - add a parameter to a method."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class IntroduceParameter(RefactoringBase):
    """Add a new parameter to a method."""

    def __init__(self, file_path: str, target: str, name: str, default: str = None):
        """Initialize the IntroduceParameter refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method (e.g., "ClassName::method_name")
            name: Name of the new parameter
            default: Default value for the new parameter (optional)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.name = name
        self.default = default
        self.source = self.file_path.read_text()
        # Parse the target specification - if it contains "::" it's "ClassName::method_name"
        if "::" not in self.target:
            raise ValueError(f"Target '{target}' must be in format 'ClassName::method_name'")
        self.class_name, self.method_name = self.parse_qualified_target(target)

    def apply(self, source: str) -> str:
        """Apply the introduce parameter refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new parameter added
        """
        self.source = source

        # Parse the source code
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Use the instance variables set in __init__
        class_name = self.class_name
        method_name = self.method_name
        modified = False

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        # Add the new parameter
                        if self.default is not None:
                            # Add as a parameter with default
                            default_node = ast.Constant(value=float(self.default))
                            item.args.defaults.append(default_node)
                            item.args.args.append(ast.arg(arg=self.name, annotation=None))
                        else:
                            # Add as a regular parameter
                            item.args.args.append(ast.arg(arg=self.name, annotation=None))
                        modified = True
                        break
                if modified:
                    break

        if not modified:
            raise ValueError(f"Could not find method '{method_name}' in class '{class_name}'")

        # Convert back to source code
        return ast.unparse(tree)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        # Check that the target method exists in the source
        return f"def {self.method_name}" in source and f"class {self.class_name}" in source
