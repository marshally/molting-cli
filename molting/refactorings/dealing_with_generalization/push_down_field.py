"""Push Down Field refactoring - move a field from superclass to specific subclasses."""

import ast
import copy
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class PushDownField(RefactoringBase):
    """Move a field from superclass to specific subclasses using AST transformation."""

    def __init__(self, file_path: str, target: str, to: str):
        """Initialize the PushDownField refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field as "ClassName::field_name"
            to: Destination subclass name
        """
        self.file_path = Path(file_path)
        self.target = target
        self.to = to
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the push down field refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with field pushed down to subclass
        """
        # Parse the superclass and field name
        class_name, field_name = self.target.split("::", 1)

        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the superclass and subclass
        super_class = None
        sub_class = None

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if node.name == class_name:
                    super_class = node
                elif node.name == self.to:
                    sub_class = node

        if not super_class:
            raise ValueError(f"Superclass '{class_name}' not found")
        if not sub_class:
            raise ValueError(f"Subclass '{self.to}' not found")

        # Find and extract the field from the superclass
        field_assignment, super_init = self._find_field_assignment_and_init(
            super_class, field_name
        )
        if not field_assignment:
            raise ValueError(f"Field '{field_name}' not found in class '{class_name}'")

        # Make a deep copy of the field assignment
        field_assignment_copy = copy.deepcopy(field_assignment)

        # Remove the field from superclass __init__
        super_init.body.remove(field_assignment)

        # If superclass __init__ body is now empty, remove the __init__ method
        if not super_init.body:
            super_class.body.remove(super_init)
            # If the class body is now empty, add a pass statement
            if not super_class.body:
                super_class.body.append(ast.Pass())

        # Add the field to subclass, creating __init__ if needed
        # The subclass __init__ should call super().__init__()
        self._add_field_to_subclass(sub_class, field_assignment_copy)

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
            # Check that both the superclass and subclass exist
            class_name, field_name = self.target.split("::", 1)
            tree = ast.parse(source)

            super_class = None
            sub_class = None

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name == class_name:
                        super_class = node
                    elif node.name == self.to:
                        sub_class = node

            if not super_class or not sub_class:
                return False

            # Check that the field exists in superclass
            return self._find_field_assignment(super_class, field_name) is not None

        except (SyntaxError, AttributeError, ValueError):
            return False

    def _find_field_assignment(self, class_node: ast.ClassDef, field_name: str):
        """Find a field assignment in a class __init__ method.

        Args:
            class_node: The ClassDef AST node
            field_name: The name of the field

        Returns:
            The assignment statement AST node or None if not found
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if (
                                    isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                    and target.attr == field_name
                                ):
                                    return stmt
        return None

    def _find_field_assignment_and_init(self, class_node: ast.ClassDef, field_name: str):
        """Find a field assignment and its containing __init__ method.

        Args:
            class_node: The ClassDef AST node
            field_name: The name of the field

        Returns:
            Tuple of (assignment statement AST node, __init__ method AST node) or (None, None) if not found
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if (
                                    isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                    and target.attr == field_name
                                ):
                                    return stmt, item
        return None, None

    def _add_field_to_subclass(self, class_node: ast.ClassDef, field_assignment: ast.stmt):
        """Add a field assignment to a subclass, creating __init__ if needed.

        The __init__ will call super().__init__() if it's newly created.

        Args:
            class_node: The ClassDef AST node
            field_assignment: The assignment statement to add
        """
        # Find or create __init__ method
        init_method = None
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method is None:
            # Create __init__ method with super().__init__() call
            super_call = ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(
                            func=ast.Name(id="super", ctx=ast.Load()),
                            args=[],
                            keywords=[],
                        ),
                        attr="__init__",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                )
            )

            init_method = ast.FunctionDef(
                name="__init__",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self", annotation=None)],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[super_call, field_assignment],
                decorator_list=[],
                returns=None,
            )

            # Remove `pass` statements from class body and insert __init__ at start
            class_node.body = [item for item in class_node.body if not (isinstance(item, ast.Pass))]
            class_node.body.insert(0, init_method)
        else:
            # Add to existing __init__, but check if super().__init__() is already called
            # If not, add it at the beginning
            has_super_call = self._has_super_init_call(init_method)
            if not has_super_call:
                super_call = ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Call(
                                func=ast.Name(id="super", ctx=ast.Load()),
                                args=[],
                                keywords=[],
                            ),
                            attr="__init__",
                            ctx=ast.Load(),
                        ),
                        args=[],
                        keywords=[],
                    )
                )
                init_method.body.insert(0, super_call)

            # Add the field assignment at the end
            init_method.body.append(field_assignment)

    def _has_super_init_call(self, init_method: ast.FunctionDef) -> bool:
        """Check if __init__ method calls super().__init__().

        Args:
            init_method: The __init__ method AST node

        Returns:
            True if super().__init__() is called, False otherwise
        """
        for stmt in init_method.body:
            if isinstance(stmt, ast.Expr):
                if isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    if isinstance(call.func, ast.Attribute):
                        if call.func.attr == "__init__":
                            if isinstance(call.func.value, ast.Call):
                                if isinstance(call.func.value.func, ast.Name):
                                    if call.func.value.func.id == "super":
                                        return True
        return False
