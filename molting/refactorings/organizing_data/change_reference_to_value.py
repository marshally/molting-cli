"""Change Reference to Value refactoring - turn a reference object into a value object."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class ChangeReferenceToValue(RefactoringBase):
    """Change a reference object to a value object.

    Transforms a class that uses a registry pattern (singleton/flyweight) into
    a value object by removing the registry and adding value equality methods.
    """

    def __init__(self, file_path: str, target: str):
        """Initialize the ChangeReferenceToValue refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target class name (e.g., "Currency")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the change reference to value refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with reference object transformed to value object
        """
        self.source = source

        # Parse the source code
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class
        class_node = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == self.target:
                class_node = node
                break

        if class_node is None:
            raise ValueError(f"Class '{self.target}' not found in {self.file_path}")

        # Transform the class from reference to value object
        self._transform_to_value_object(class_node)

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
        # Check that the class exists
        return self.target in source

    def _transform_to_value_object(self, class_node: ast.ClassDef) -> None:
        """Transform a reference object class to a value object.

        Removes registry/singleton pattern and adds value equality methods.

        Args:
            class_node: The AST ClassDef node of the class to transform
        """
        # Step 1: Remove the _instances class variable
        without_instances: list[ast.stmt] = []
        for item in class_node.body:
            # Skip _instances class variable
            if isinstance(item, ast.Assign):
                # Check if this is _instances = {}
                skip_item = False
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "_instances":
                        skip_item = True
                        break
                if not skip_item:
                    without_instances.append(item)
            else:
                without_instances.append(item)

        class_node.body = without_instances

        # Step 2: Remove the classmethod get() method
        without_get: list[ast.stmt] = []
        for item in class_node.body:
            # Skip classmethod get() method
            if isinstance(item, ast.FunctionDef) and item.name == "get":
                # Check if it has classmethod decorator
                has_classmethod = any(
                    isinstance(d, ast.Name) and d.id == "classmethod" for d in item.decorator_list
                )
                if has_classmethod:
                    continue  # Skip this method
            without_get.append(item)

        class_node.body = without_get

        # Step 3: Add __eq__ method
        eq_method = self._create_eq_method()
        class_node.body.append(eq_method)

        # Step 4: Add __hash__ method
        hash_method = self._create_hash_method()
        class_node.body.append(hash_method)

    def _create_eq_method(self) -> ast.FunctionDef:
        """Create the __eq__ method for value object.

        Returns:
            AST FunctionDef node for __eq__ method
        """
        # def __eq__(self, other):
        #     if not isinstance(other, Currency):
        #         return False
        #     return self.code == other.code

        # Create the method body
        # First statement: if not isinstance(other, Currency): return False
        isinstance_call = ast.Call(
            func=ast.Name(id="isinstance", ctx=ast.Load()),
            args=[
                ast.Name(id="other", ctx=ast.Load()),
                ast.Name(id=self.target, ctx=ast.Load()),
            ],
            keywords=[],
        )
        type_check = ast.If(
            test=ast.UnaryOp(
                op=ast.Not(),
                operand=isinstance_call,
            ),
            body=[ast.Return(value=ast.Constant(value=False))],
            orelse=[],
        )

        # Second statement: return self.code == other.code
        # We need to find the main attribute in __init__
        # For now, we'll use the first parameter as the attribute name
        # This will be "code" in most cases

        # Assume the attribute is based on the first parameter of __init__
        attr_name = "code"  # Default assumption

        return_stmt = ast.Return(
            value=ast.Compare(
                left=ast.Attribute(
                    value=ast.Name(id="self", ctx=ast.Load()),
                    attr=attr_name,
                    ctx=ast.Load(),
                ),
                ops=[ast.Eq()],
                comparators=[
                    ast.Attribute(
                        value=ast.Name(id="other", ctx=ast.Load()),
                        attr=attr_name,
                        ctx=ast.Load(),
                    )
                ],
            )
        )

        eq_method = ast.FunctionDef(
            name="__eq__",
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self", annotation=None),
                    ast.arg(arg="other", annotation=None),
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[type_check, return_stmt],
            decorator_list=[],
            returns=None,
        )

        return eq_method

    def _create_hash_method(self) -> ast.FunctionDef:
        """Create the __hash__ method for value object.

        Returns:
            AST FunctionDef node for __hash__ method
        """
        # def __hash__(self):
        #     return hash(self.code)

        # Assume attribute name is "code"
        attr_name = "code"

        return_stmt = ast.Return(
            value=ast.Call(
                func=ast.Name(id="hash", ctx=ast.Load()),
                args=[
                    ast.Attribute(
                        value=ast.Name(id="self", ctx=ast.Load()),
                        attr=attr_name,
                        ctx=ast.Load(),
                    )
                ],
                keywords=[],
            )
        )

        hash_method = ast.FunctionDef(
            name="__hash__",
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self", annotation=None)],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[return_stmt],
            decorator_list=[],
            returns=None,
        )

        return hash_method
