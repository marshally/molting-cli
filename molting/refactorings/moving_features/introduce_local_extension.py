"""Introduce Local Extension refactoring - create subclass or wrapper with new methods."""

import ast
from pathlib import Path
from typing import List, Tuple, cast

from molting.core.refactoring_base import RefactoringBase


class IntroduceLocalExtension(RefactoringBase):
    """Create a subclass or wrapper to add methods to a class you can't modify."""

    def __init__(
        self,
        file_path: str,
        target: str,
        name: str,
        extension_type: str = "subclass",
    ):
        """Initialize the IntroduceLocalExtension refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: The base class name to extend (e.g., "date")
            name: Name of the new extension class (e.g., "MfDate")
            extension_type: Type of extension ("subclass" or "wrapper")
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.target_class = target
        self.extension_class_name = name
        self.extension_type = extension_type

    def apply(self, source: str) -> str:
        """Apply the introduce local extension refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new extension class created
        """
        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find all helper functions that operate on the target class
        helper_functions = self._find_helper_functions(tree, self.target_class)

        if not helper_functions:
            raise ValueError(f"No helper functions found for '{self.target_class}'")

        # Extract the first parameter name from helper functions to identify target instances
        target_param = self._extract_target_parameter(helper_functions)

        # Create the extension class with extracted methods
        extension_class = self._create_extension_class(helper_functions, target_param)

        # Add the extension class to the tree
        self._add_extension_class(tree, extension_class)

        # Update function calls to use the extension class methods
        self._update_function_calls(tree, helper_functions, self.extension_class_name)

        # Remove or comment out the helper functions
        self._remove_helper_functions(tree, helper_functions)

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
            tree = ast.parse(source)
            helper_functions = self._find_helper_functions(tree, self.target_class)
            return len(helper_functions) > 0
        except Exception:
            return False

    def _find_helper_functions(
        self, tree: ast.Module, target_class: str
    ) -> List[Tuple[str, ast.FunctionDef]]:
        """Find helper functions that take the target class as first parameter.

        Args:
            tree: The AST module
            target_class: Name of the target class

        Returns:
            List of (function_name, function_node) tuples
        """
        helper_functions = []

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Check if function has at least one parameter
                if len(node.args.args) > 0:
                    # Get the first parameter name
                    first_param = node.args.args[0].arg
                    # Check if the function is a helper for the target class
                    # by looking for uses of the first parameter in the function body
                    if self._uses_parameter(node, first_param, target_class):
                        helper_functions.append((node.name, node))

        return helper_functions

    def _uses_parameter(
        self, func_node: ast.FunctionDef, param_name: str, target_class: str
    ) -> bool:
        """Check if a function uses the parameter in a way that suggests it's the target class.

        Args:
            func_node: The function node
            param_name: Name of the parameter to check
            target_class: Name of the target class

        Returns:
            True if the parameter is used in the function
        """
        for node in ast.walk(func_node):
            if isinstance(node, ast.Name) and node.id == param_name:
                return True
        return False

    def _extract_target_parameter(self, helper_functions: List[Tuple[str, ast.FunctionDef]]) -> str:
        """Extract the target parameter name from helper functions.

        Args:
            helper_functions: List of helper functions

        Returns:
            Name of the target parameter
        """
        if helper_functions:
            _, first_func = helper_functions[0]
            if len(first_func.args.args) > 0:
                return first_func.args.args[0].arg
        return "self"

    def _create_extension_class(
        self, helper_functions: List[Tuple[str, ast.FunctionDef]], target_param: str
    ) -> ast.ClassDef:
        """Create the extension class with methods extracted from helper functions.

        Args:
            helper_functions: List of helper functions
            target_param: Name of the target parameter

        Returns:
            A new ClassDef node
        """
        methods = []

        for func_name, func_node in helper_functions:
            # Convert the function to a method by:
            # 1. Renaming first parameter to 'self'
            # 2. Keeping the function body
            method = self._function_to_method(func_node, target_param)
            methods.append(method)

        # Create the class with the target class as base
        base = ast.Name(id=self.target_class, ctx=ast.Load())
        body: list[ast.stmt] = cast(
            list[ast.stmt], methods if methods else [ast.Pass()]  # type: ignore[list-item]
        )
        extension_class = ast.ClassDef(
            name=self.extension_class_name,
            bases=[base],
            keywords=[],
            body=body,
            decorator_list=[],
        )

        return extension_class

    def _function_to_method(self, func_node: ast.FunctionDef, target_param: str) -> ast.FunctionDef:
        """Convert a function to a method by renaming the first parameter to 'self'.

        Args:
            func_node: The function node
            target_param: Name of the current first parameter

        Returns:
            A new FunctionDef node (method)
        """
        # Create a copy of the function node
        method = ast.FunctionDef(
            name=func_node.name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="self", annotation=None)] + func_node.args.args[1:],
                vararg=func_node.args.vararg,
                kwonlyargs=func_node.args.kwonlyargs,
                kw_defaults=func_node.args.kw_defaults,
                kwarg=func_node.args.kwarg,
                defaults=func_node.args.defaults,
            ),
            body=self._replace_parameter_in_body(func_node.body, target_param, "self"),
            decorator_list=func_node.decorator_list,
            returns=func_node.returns,
            type_comment=func_node.type_comment,
        )

        return method

    def _replace_parameter_in_body(
        self, body: List[ast.stmt], old_param: str, new_param: str
    ) -> List[ast.stmt]:
        """Replace parameter names in the function body.

        Args:
            body: List of statements
            old_param: Old parameter name
            new_param: New parameter name

        Returns:
            Updated list of statements
        """

        class ParameterReplacer(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name) -> ast.expr:
                if node.id == old_param:
                    return ast.Name(id=new_param, ctx=node.ctx)
                return node

        replacer = ParameterReplacer()
        return [replacer.visit(stmt) for stmt in body]

    def _add_extension_class(self, tree: ast.Module, extension_class: ast.ClassDef) -> None:
        """Add the extension class to the AST tree after imports.

        Args:
            tree: The AST module
            extension_class: The new extension class
        """
        # Find the position to insert the class (after imports)
        insert_index = 0
        for i, node in enumerate(tree.body):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                insert_index = i + 1
            elif not isinstance(node, (ast.Import, ast.ImportFrom)):
                break

        # Insert the extension class
        tree.body.insert(insert_index, extension_class)

    def _update_function_calls(
        self, tree: ast.Module, helper_functions: List[Tuple[str, ast.FunctionDef]], class_name: str
    ) -> None:
        """Update function calls to use the extension class methods.

        Args:
            tree: The AST module
            helper_functions: List of helper functions
            class_name: Name of the extension class
        """
        function_names = {name for name, _ in helper_functions}
        target_class = self.target_class

        class CallUpdater(ast.NodeTransformer):
            def visit_Call(self, node: ast.Call) -> ast.expr:
                # First, visit children
                updated = self.generic_visit(node)
                if not isinstance(updated, ast.Call):
                    return updated  # type: ignore[return-value]
                node = updated

                # Check if this is a call to one of the helper functions
                if isinstance(node.func, ast.Name) and node.func.id in function_names:
                    # Check if the first argument exists
                    if node.args:
                        # Convert to method call: obj.method_name(remaining_args)
                        first_arg = node.args[0]
                        remaining_args = node.args[1:]

                        # Create the method call
                        method_call = ast.Call(
                            func=ast.Attribute(
                                value=first_arg,
                                attr=node.func.id,
                                ctx=ast.Load(),
                            ),
                            args=remaining_args,
                            keywords=node.keywords,
                        )

                        return method_call

                # Also check if this is a constructor call to the target class
                if isinstance(node.func, ast.Name) and node.func.id == target_class:
                    # Replace with the extension class constructor
                    return ast.Call(
                        func=ast.Name(id=class_name, ctx=ast.Load()),
                        args=node.args,
                        keywords=node.keywords,
                    )

                return node

        updater = CallUpdater()
        for i, node in enumerate(tree.body):
            tree.body[i] = updater.visit(node)

    def _remove_helper_functions(
        self, tree: ast.Module, helper_functions: List[Tuple[str, ast.FunctionDef]]
    ) -> None:
        """Remove helper functions from the AST tree.

        Args:
            tree: The AST module
            helper_functions: List of helper functions to remove
        """
        function_names = {name for name, _ in helper_functions}

        # Remove functions with matching names
        tree.body = [
            node
            for node in tree.body
            if not (isinstance(node, ast.FunctionDef) and node.name in function_names)
        ]
