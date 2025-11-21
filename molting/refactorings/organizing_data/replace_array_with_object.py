"""Replace Array with Object refactoring - turn array access into object attributes."""

import ast
from pathlib import Path
from typing import Dict, List

from molting.core.refactoring_base import RefactoringBase


class ReplaceArrayWithObject(RefactoringBase):
    """Replace array/list access with object attribute access."""

    def __init__(self, file_path: str, target: str, class_name: str, fields: str):
        """Initialize the ReplaceArrayWithObject refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target variable in function (e.g., "function_name::variable_name")
            class_name: Name of the new class to create
            fields: Comma-separated field names (e.g., "name,wins,losses")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.class_name = class_name
        self.fields = [f.strip() for f in fields.split(",")]
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the replace array with object refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new object class and attribute access
        """
        self.source = source

        if "::" not in self.target:
            raise ValueError(
                f"Target must be in format 'function_name::variable_name', got '{self.target}'"
            )

        function_name, variable_name = self.target.split("::", 1)

        # Parse the source code
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target function
        function_node = None
        function_index = None
        for idx, node in enumerate(tree.body):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                function_node = node
                function_index = idx
                break

        if function_node is None:
            raise ValueError(f"Function '{function_name}' not found in {self.file_path}")

        # Step 1: Create the new class
        new_class = self._create_data_class(variable_name)

        # Step 2: Update the function to use the new class
        self._update_function(function_node, variable_name)

        # Step 3: Insert the new class before the function
        tree.body.insert(function_index, new_class)

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
        if "::" not in self.target:
            return False
        function_name, variable_name = self.target.split("::", 1)
        return function_name in source and variable_name in source

    def _collect_array_indices(self, function_node: ast.FunctionDef, var_name: str) -> Dict[int, str]:
        """Collect information about array indexing patterns.

        Args:
            function_node: The function AST node
            var_name: The variable name being indexed

        Returns:
            Dictionary mapping index to field name
        """
        indices = {}

        class IndexCollector(ast.NodeVisitor):
            def visit_Subscript(self, node):
                if isinstance(node.value, ast.Name) and node.value.id == var_name:
                    if isinstance(node.slice, ast.Constant):
                        idx = node.slice.value
                        if isinstance(idx, int):
                            # Try to determine field name from context
                            # Look for assignments like: name = var[0]
                            indices[idx] = f"field_{idx}"
                self.generic_visit(node)

        collector = IndexCollector()
        collector.visit(function_node)
        return indices

    def _create_data_class(self, var_name: str) -> ast.ClassDef:
        """Create a new data class to replace array access.

        Args:
            var_name: The original variable name (used for naming the new param)

        Returns:
            AST ClassDef node for the new data class
        """
        # Create __init__ method with all fields as parameters
        init_args = [ast.arg(arg="self", annotation=None)]
        init_args.extend([ast.arg(arg=field, annotation=None) for field in self.fields])

        init_body = []
        for field in self.fields:
            init_body.append(
                ast.Assign(
                    targets=[
                        ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr=field,
                            ctx=ast.Store(),
                        )
                    ],
                    value=ast.Name(id=field, ctx=ast.Load()),
                )
            )

        init_method = ast.FunctionDef(
            name="__init__",
            args=ast.arguments(
                posonlyargs=[],
                args=init_args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=init_body,
            decorator_list=[],
            returns=None,
        )

        # Create the class
        class_def = ast.ClassDef(
            name=self.class_name,
            bases=[],
            keywords=[],
            body=[init_method],
            decorator_list=[],
        )

        return class_def

    def _update_function(self, function_node: ast.FunctionDef, var_name: str) -> None:
        """Update the function to use the new class instead of array indexing.

        Args:
            function_node: The function AST node
            var_name: The variable name being replaced
        """
        # Find the parameter and rename it (if it's a parameter)
        # In our case, rename 'row' to lowercase of class_name or use provided name
        new_param_name = self.class_name[0].lower() + self.class_name[1:] if self.class_name else var_name

        # Update parameter name in function signature
        for arg in function_node.args.args:
            if arg.arg == var_name:
                arg.arg = new_param_name
                break

        # Replace all subscript accesses with attribute accesses
        fields = self.fields
        var_name_outer = var_name

        class SubscriptReplacer(ast.NodeTransformer):
            def visit_Subscript(self, node):
                self.generic_visit(node)
                if isinstance(node.value, ast.Name) and node.value.id == var_name_outer:
                    # Replace var[index] with var.field_name
                    if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                        idx = node.slice.value
                        if idx < len(fields):
                            return ast.Attribute(
                                value=ast.Name(id=new_param_name, ctx=ast.Load()),
                                attr=fields[idx],
                                ctx=node.ctx,
                            )
                return node

        replacer = SubscriptReplacer()
        for i, stmt in enumerate(function_node.body):
            function_node.body[i] = replacer.visit(stmt)

    def _infer_field_names(self, source: str, function_name: str, var_name: str) -> List[str]:
        """Try to infer field names from variable assignments.

        Args:
            source: The source code
            function_name: Name of the function
            var_name: Name of the array variable

        Returns:
            List of inferred field names
        """
        try:
            tree = ast.parse(source)
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    field_names = [""] * 10  # Max 10 fields
                    for stmt in node.body:
                        if isinstance(stmt, ast.Assign):
                            # Look for assignments like: name = row[0]
                            if isinstance(stmt.value, ast.Subscript):
                                if isinstance(stmt.value.value, ast.Name) and stmt.value.value.id == var_name:
                                    if isinstance(stmt.value.slice, ast.Constant):
                                        idx = stmt.value.slice.value
                                        if isinstance(idx, int) and isinstance(stmt.targets[0], ast.Name):
                                            field_name = stmt.targets[0].id
                                            if idx < len(field_names):
                                                field_names[idx] = field_name

                    # Filter out empty names
                    return [name for name in field_names if name]
        except Exception:
            pass

        return self.fields
