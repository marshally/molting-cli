"""Change Value to Reference refactoring - turn a value object into a reference object."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class ChangeValueToReference(RefactoringBase):
    """Change a value object to a reference object.

    Converts a value object (instantiated multiple times) into a reference object
    (shared instance via registry) using the Registry pattern.
    """

    def __init__(self, file_path: str, target: str):
        """Initialize the ChangeValueToReference refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target class name to convert (e.g., "Customer")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the change value to reference refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with reference object pattern applied
        """
        self.source = source

        # Parse the source code
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class
        target_class = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == self.target:
                target_class = node
                break

        if target_class is None:
            raise ValueError(f"Class '{self.target}' not found in {self.file_path}")

        # Step 1: Update all constructors that instantiate this class to use get_named
        # Do this BEFORE adding the method so we don't transform calls inside get_named
        self._update_constructors_to_use_registry(tree, target_class.name)

        # Step 2: Add _instances class variable and get_named classmethod to target class
        self._add_registry_to_class(target_class)

        # Fix missing location information in the AST
        ast.fix_missing_locations(tree)

        # Unparse the modified AST back to source code
        refactored = ast.unparse(tree)
        return refactored

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        return self.target in source

    def _add_registry_to_class(self, class_node: ast.ClassDef) -> None:
        """Add _instances registry and get_named classmethod to the class.

        Args:
            class_node: The AST ClassDef node of the target class
        """
        # Create class variable: _instances = {}
        instances_var = ast.Assign(
            targets=[ast.Name(id="_instances", ctx=ast.Store())],
            value=ast.Dict(keys=[], values=[]),
        )

        # Create get_named classmethod
        get_named_method = self._create_get_named_method()

        # Insert _instances before __init__ and get_named after __init__
        init_index = None
        for i, item in enumerate(class_node.body):
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_index = i
                break

        # If __init__ found, insert instances before it and get_named after it
        if init_index is not None:
            class_node.body.insert(init_index, instances_var)
            # After inserting instances_var, __init__ is now at init_index + 1
            # So insert get_named after __init__
            class_node.body.insert(init_index + 2, get_named_method)
        else:
            class_node.body.append(instances_var)
            class_node.body.append(get_named_method)

    def _create_get_named_method(self) -> ast.FunctionDef:
        """Create the get_named classmethod.

        Returns:
            AST FunctionDef node for get_named classmethod
        """
        # def get_named(cls, name):
        #     if name not in cls._instances:
        #         cls._instances[name] = ClassName(name)
        #     return cls._instances[name]

        # Create the method body
        method_body = [
            # if name not in cls._instances:
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="name", ctx=ast.Load()),
                    ops=[ast.NotIn()],
                    comparators=[
                        ast.Attribute(
                            value=ast.Name(id="cls", ctx=ast.Load()),
                            attr="_instances",
                            ctx=ast.Load(),
                        )
                    ],
                ),
                body=[
                    # cls._instances[name] = ClassName(name)
                    ast.Assign(
                        targets=[
                            ast.Subscript(
                                value=ast.Attribute(
                                    value=ast.Name(id="cls", ctx=ast.Load()),
                                    attr="_instances",
                                    ctx=ast.Load(),
                                ),
                                slice=ast.Name(id="name", ctx=ast.Load()),
                                ctx=ast.Store(),
                            )
                        ],
                        value=ast.Call(
                            func=ast.Name(id=self.target, ctx=ast.Load()),
                            args=[ast.Name(id="name", ctx=ast.Load())],
                            keywords=[],
                        ),
                    )
                ],
                orelse=[],
            ),
            # return cls._instances[name]
            ast.Return(
                value=ast.Subscript(
                    value=ast.Attribute(
                        value=ast.Name(id="cls", ctx=ast.Load()),
                        attr="_instances",
                        ctx=ast.Load(),
                    ),
                    slice=ast.Name(id="name", ctx=ast.Load()),
                    ctx=ast.Load(),
                )
            ),
        ]

        # Create the function definition
        get_named = ast.FunctionDef(
            name="get_named",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="cls", annotation=None),
                    ast.arg(arg="name", annotation=None),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=method_body,
            decorator_list=[ast.Name(id="classmethod", ctx=ast.Load())],
            returns=None,
        )

        return get_named

    def _update_constructors_to_use_registry(self, tree: ast.AST, class_name: str) -> None:
        """Update all constructor calls of the target class to use get_named.

        Args:
            tree: The AST tree to search
            class_name: Name of the class to update calls for
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check if this is an assignment with a call to the target class
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == class_name:
                        # Replace ClassName(arg) with ClassName.get_named(arg)
                        if len(node.value.args) == 1:
                            arg = node.value.args[0]
                            # Only update direct instantiations with a single argument
                            node.value = ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id=class_name, ctx=ast.Load()),
                                    attr="get_named",
                                    ctx=ast.Load(),
                                ),
                                args=[arg],
                                keywords=[],
                            )
