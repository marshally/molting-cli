"""Pull Up Field refactoring - move a field from subclasses to the superclass."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class PullUpField(RefactoringBase):
    """Pull up a field from subclasses to the superclass using AST transformation."""

    def __init__(self, file_path: str, target: str, to: str):
        """Initialize the PullUpField refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field as "ClassName::field_name"
            to: Superclass name where the field will be moved
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.target_spec = target
        self.superclass_name = to

    def apply(self, source: str) -> str:
        """Apply the pull up field refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with field pulled up to superclass
        """
        # Parse the target class and field name
        class_name, field_name = self.target_spec.split("::", 1)

        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find all classes in the tree
        classes_by_name = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes_by_name[node.name] = node

        if class_name not in classes_by_name:
            raise ValueError(f"Class '{class_name}' not found")
        if self.superclass_name not in classes_by_name:
            raise ValueError(f"Superclass '{self.superclass_name}' not found")

        subclass = classes_by_name[class_name]
        superclass = classes_by_name[self.superclass_name]

        # Find the field assignment in the target subclass __init__
        field_assignment, subclass_init = self._find_field_assignment_and_init(subclass, field_name)
        if not field_assignment:
            raise ValueError(f"Field '{field_name}' not found in class '{class_name}'")

        # Extract the field value from the assignment
        field_value = field_assignment.value
        # Get the parameter name if it's a simple assignment from a parameter
        param_name = self._extract_param_name(field_value)

        # Find all other subclasses of the superclass that have the same field
        other_subclasses_with_field = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name != class_name:
                # Check if this is a subclass of the superclass
                if self._is_subclass_of(node, self.superclass_name):
                    if self._find_field_assignment(node, field_name):
                        other_subclasses_with_field.append(node)

        # Remove the field from the target subclass __init__
        subclass_init.body.remove(field_assignment)

        # Add the field to superclass __init__
        self._add_field_to_superclass(superclass, field_name, param_name)

        # Update target subclass __init__ to call super().__init__()
        self._update_subclass_init(subclass_init, param_name)

        # Update all other subclasses with the same field
        for other_subclass in other_subclasses_with_field:
            other_field_assignment, other_init = self._find_field_assignment_and_init(
                other_subclass, field_name
            )
            if other_field_assignment and other_init:
                other_init.body.remove(other_field_assignment)
                self._update_subclass_init(other_init, param_name)

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
            # Check that both the subclass and superclass exist
            class_name, field_name = self.target_spec.split("::", 1)
            tree = ast.parse(source)

            subclass = None
            superclass = None

            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    if node.name == class_name:
                        subclass = node
                    elif node.name == self.superclass_name:
                        superclass = node

            if not subclass or not superclass:
                return False

            # Check that the field exists in the subclass
            return self._find_field_assignment(subclass, field_name) is not None

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
            Tuple of (assignment statement AST node, __init__ method AST node)
            or (None, None) if not found
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

    def _extract_param_name(self, value_node: ast.expr) -> str:
        """Extract the parameter name from an assignment value.

        Args:
            value_node: The AST node representing the value being assigned

        Returns:
            The parameter name if it's a simple Name node, empty string otherwise
        """
        if isinstance(value_node, ast.Name):
            return value_node.id
        return ""

    def _is_subclass_of(self, class_node: ast.ClassDef, superclass_name: str) -> bool:
        """Check if a class is a subclass of the given superclass.

        Args:
            class_node: The ClassDef AST node
            superclass_name: The name of the superclass

        Returns:
            True if class_node inherits from superclass_name, False otherwise
        """
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == superclass_name:
                return True
        return False

    def _add_field_to_superclass(
        self, superclass_node: ast.ClassDef, field_name: str, param_name: str
    ):
        """Add a field assignment to the superclass __init__.

        Args:
            superclass_node: The ClassDef AST node for the superclass
            field_name: The name of the field to add
            param_name: The parameter name to assign from (e.g., "name")
        """
        # Find or create __init__ method
        init_method = None
        for item in superclass_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method is None:
            # Create __init__ method with the parameter
            field_assignment = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Store()),
                        attr=field_name,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Name(id=param_name, ctx=ast.Load()),
            )

            init_method = ast.FunctionDef(
                name="__init__",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[
                        ast.arg(arg="self", annotation=None),
                        ast.arg(arg=param_name, annotation=None),
                    ],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[field_assignment],
                decorator_list=[],
                returns=None,
            )

            # Remove `pass` statements and insert __init__ at start
            superclass_node.body = [
                item for item in superclass_node.body if not isinstance(item, ast.Pass)
            ]
            superclass_node.body.insert(0, init_method)
        else:
            # Add parameter to existing __init__ if not already present
            param_arg_names = [arg.arg for arg in init_method.args.args]
            if param_name not in param_arg_names:
                init_method.args.args.append(ast.arg(arg=param_name, annotation=None))

            # Add field assignment at the beginning of __init__
            field_assignment = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Store()),
                        attr=field_name,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Name(id=param_name, ctx=ast.Load()),
            )
            init_method.body.insert(0, field_assignment)

    def _update_subclass_init(self, init_method: ast.FunctionDef, param_name: str):
        """Update subclass __init__ to call super().__init__().

        Args:
            init_method: The __init__ method AST node of the subclass
            param_name: The parameter name to pass to super().__init__()
        """
        # Create super().__init__(param_name) call
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
                args=[ast.Name(id=param_name, ctx=ast.Load())],
                keywords=[],
            )
        )

        # Add the super call at the beginning of __init__
        init_method.body.insert(0, super_call)
