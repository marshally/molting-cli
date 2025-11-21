"""Push Down Method refactoring - move a method from superclass to subclasses."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class PushDownMethod(RefactoringBase):
    """Move a method from a superclass to specific subclasses that need it."""

    def __init__(self, file_path: str, target: str, to: str):
        """Initialize the PushDownMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification in format "ClassName::method_name"
            to: Comma-separated list of subclass names to receive the method
        """
        self.file_path = Path(file_path)
        self.target = target
        self.to = to
        self.source = self.file_path.read_text()

        # Parse the target
        try:
            self.class_name, self.method_name = self.parse_qualified_target(target)
        except ValueError:
            raise ValueError(f"Invalid target format: {target}")

        # Parse the subclass names
        self.subclass_names = [name.strip() for name in to.split(",")]

    def apply(self, source: str) -> str:
        """Apply the push down method refactoring.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with method moved to subclasses
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the superclass
        super_class = self.find_class_def(tree, self.class_name)
        if not super_class:
            raise ValueError(f"Class '{self.class_name}' not found")

        # Find the method in the superclass
        method = self.find_method_in_class(super_class, self.method_name)
        if not method:
            raise ValueError(f"Method '{self.method_name}' not found in class '{self.class_name}'")

        # Find all subclasses
        subclasses = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == self.class_name:
                        subclasses[node.name] = node
                    elif isinstance(base, ast.Attribute):
                        # Handle qualified names like module.ClassName
                        if self._get_name_from_node(base) == self.class_name:
                            subclasses[node.name] = node

        # Check that all specified subclasses exist
        for subclass_name in self.subclass_names:
            if subclass_name not in subclasses:
                raise ValueError(f"Subclass '{subclass_name}' not found")

        # Clone the method
        cloned_method = ast.parse(ast.unparse(method)).body[0]

        # Remove the method from the superclass
        super_class.body.remove(method)

        # If the superclass body is now empty or only has pass, add pass back
        if not super_class.body:
            super_class.body.append(ast.Pass())

        # Add the method to each specified subclass
        for subclass_name in self.subclass_names:
            subclass_node = subclasses[subclass_name]

            # Remove pass statement if it's the only thing in the subclass
            if len(subclass_node.body) == 1 and isinstance(subclass_node.body[0], ast.Pass):
                subclass_node.body.pop()

            # Clone and add the method
            method_clone = ast.parse(ast.unparse(cloned_method)).body[0]
            subclass_node.body.append(method_clone)

        # Return the unparsed tree
        return ast.unparse(tree)

    def _get_name_from_node(self, node: ast.expr) -> str:
        """Extract the name from an AST node (supports qualified names)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return False

        # Check that superclass exists
        super_class = self.find_class_def(tree, self.class_name)
        if not super_class:
            return False

        # Check that method exists in superclass
        method = self.find_method_in_class(super_class, self.method_name)
        if not method:
            return False

        # Check that all subclasses exist
        found_subclasses = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == self.class_name:
                        found_subclasses.add(node.name)
                    elif isinstance(base, ast.Attribute):
                        if self._get_name_from_node(base) == self.class_name:
                            found_subclasses.add(node.name)

        for subclass_name in self.subclass_names:
            if subclass_name not in found_subclasses:
                return False

        return True
