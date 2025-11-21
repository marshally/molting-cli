"""Extract Superclass refactoring - create a superclass from common features."""

import ast
from pathlib import Path
from typing import List, Set, Tuple

from molting.core.refactoring_base import RefactoringBase


class ExtractSuperclass(RefactoringBase):
    """Create a superclass and move common features from multiple classes to it."""

    def __init__(self, file_path: str, targets: str, name: str):
        """Initialize the ExtractSuperclass refactoring.

        Args:
            file_path: Path to the Python file to refactor
            targets: Comma-separated list of class names to extract common features from
            name: Name of the new superclass to create
        """
        self.file_path = Path(file_path)
        self.class_names = [c.strip() for c in targets.split(",")]
        self.superclass_name = name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the extract superclass refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with superclass created
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find all target classes
        target_classes = {}
        for class_name in self.class_names:
            class_node = self.find_class_def(tree, class_name)
            if not class_node:
                raise ValueError(f"Class '{class_name}' not found")
            target_classes[class_name] = class_node

        # Find common features
        common_init_params, common_methods = self._find_common_features(target_classes)

        # Create the superclass
        superclass_node = self._create_superclass_node(
            target_classes, common_init_params, common_methods
        )

        # Update target classes to inherit from superclass and remove common features
        for class_name in self.class_names:
            class_node = target_classes[class_name]
            self._update_target_class(
                class_node, common_init_params, common_methods
            )

        # Find the index of the first target class and insert superclass before it
        first_target_index = None
        first_class_name = self.class_names[0]

        for i, node in enumerate(tree.body):
            if isinstance(node, ast.ClassDef) and node.name == first_class_name:
                first_target_index = i
                break

        if first_target_index is None:
            raise ValueError(f"Could not find class {first_class_name}")

        tree.body.insert(first_target_index, superclass_node)

        # Fix missing location information in the AST
        ast.fix_missing_locations(tree)

        # Convert modified AST back to source code
        return ast.unparse(tree)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)
            for class_name in self.class_names:
                if not self.find_class_def(tree, class_name):
                    return False
            return len(self.class_names) >= 2
        except SyntaxError:
            return False

    def _find_common_features(self, target_classes: dict) -> Tuple[Set[str], Set[str]]:
        """Find common fields and methods across target classes.

        Args:
            target_classes: Dictionary of class name -> ClassDef nodes

        Returns:
            Tuple of (common_init_params, common_methods)
        """
        # Find init parameters
        init_params_by_class = {}
        for class_name, class_node in target_classes.items():
            params = self._get_init_params(class_node)
            init_params_by_class[class_name] = params

        # Find common init parameters (excluding 'self')
        common_init_params = None
        for params in init_params_by_class.values():
            param_set = set(params) - {"self"}
            if common_init_params is None:
                common_init_params = param_set
            else:
                common_init_params &= param_set

        # Find common methods (excluding __init__)
        methods_by_class = {}
        for class_name, class_node in target_classes.items():
            methods = self._get_methods(class_node)
            methods_by_class[class_name] = methods

        common_methods = None
        for methods in methods_by_class.values():
            method_set = set(methods) - {"__init__"}
            if common_methods is None:
                common_methods = method_set
            else:
                common_methods &= method_set

        return common_init_params or set(), common_methods or set()

    def _get_init_params(self, class_node: ast.ClassDef) -> List[str]:
        """Get __init__ method parameters for a class.

        Args:
            class_node: The ClassDef AST node

        Returns:
            List of parameter names
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                return [arg.arg for arg in item.args.args]
        return []

    def _get_methods(self, class_node: ast.ClassDef) -> List[str]:
        """Get method names for a class.

        Args:
            class_node: The ClassDef AST node

        Returns:
            List of method names
        """
        methods = []
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        return methods

    def _create_superclass_node(
        self,
        target_classes: dict,
        common_init_params: Set[str],
        common_methods: Set[str],
    ) -> ast.ClassDef:
        """Create the superclass AST node.

        Args:
            target_classes: Dictionary of class name -> ClassDef nodes
            common_init_params: Set of common init parameters
            common_methods: Set of common method names

        Returns:
            AST ClassDef node for the superclass
        """
        superclass = ast.ClassDef(
            name=self.superclass_name,
            bases=[],
            keywords=[],
            body=[],
            decorator_list=[],
        )

        # Create __init__ method with common parameters
        sorted_params = sorted(common_init_params)
        init_args = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="self", annotation=None)]
            + [ast.arg(arg=p, annotation=None) for p in sorted_params],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )

        init_body = []
        for param in sorted_params:
            # self.param = param
            assign = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=param,
                        ctx=ast.Store(),
                    )
                ],
                value=ast.Name(id=param, ctx=ast.Load()),
            )
            init_body.append(assign)

        init_method = ast.FunctionDef(
            name="__init__",
            args=init_args,
            body=init_body if init_body else [ast.Pass()],
            decorator_list=[],
            returns=None,
        )

        superclass.body.append(init_method)

        # Add common methods from the first target class
        first_class = target_classes[self.class_names[0]]
        for item in first_class.body:
            if isinstance(item, ast.FunctionDef) and item.name in common_methods:
                # Deep copy the method to avoid sharing AST nodes
                method_copy = ast.fix_missing_locations(
                    ast.copy_location(
                        ast.FunctionDef(
                            name=item.name,
                            args=item.args,
                            body=item.body,
                            decorator_list=item.decorator_list,
                            returns=item.returns,
                        ),
                        item,
                    )
                )
                superclass.body.append(method_copy)

        return superclass

    def _update_target_class(
        self,
        class_node: ast.ClassDef,
        common_init_params: Set[str],
        common_methods: Set[str],
    ) -> None:
        """Update a target class to inherit from superclass.

        Args:
            class_node: The ClassDef AST node to update
            common_init_params: Set of common init parameters
            common_methods: Set of common method names
        """
        # Make class inherit from superclass
        class_node.bases = [ast.Name(id=self.superclass_name, ctx=ast.Load())]

        # Update __init__ method
        for i, item in enumerate(class_node.body):
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                # Create super().__init__() call with common parameters
                sorted_params = sorted(common_init_params)
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
                        args=[ast.Name(id=p, ctx=ast.Load()) for p in sorted_params],
                        keywords=[],
                    )
                )

                # Remove common parameter assignments from __init__ and insert super() call
                new_body = []
                for stmt in item.body:
                    # Check if this is an assignment to a common parameter
                    is_common_assignment = False
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute):
                                if (
                                    isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                    and target.attr in common_init_params
                                ):
                                    is_common_assignment = True
                                    break

                    if not is_common_assignment:
                        new_body.append(stmt)

                # Insert super() call at the beginning
                item.body = [super_call] + new_body

        # Remove common methods from the class
        new_body = []
        for stmt in class_node.body:
            if isinstance(stmt, ast.FunctionDef) and stmt.name in common_methods:
                continue
            new_body.append(stmt)

        class_node.body = new_body if new_body else [ast.Pass()]
