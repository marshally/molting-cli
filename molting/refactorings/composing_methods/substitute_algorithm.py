"""Substitute Algorithm refactoring - replace an entire algorithm with a clearer one."""

import ast
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class SubstituteAlgorithm(RefactoringBase):
    """Replace the implementation of a function/method with a clearer or more efficient one."""

    def __init__(self, file_path: str, target: str, new_body: str = ""):
        """Initialize the SubstituteAlgorithm refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target function/method name (e.g., "found_person" or "Class::method")
            new_body: Optional new implementation code as a string. If not provided,
                     will attempt to automatically transform the algorithm.
        """
        self.file_path = Path(file_path)
        self.target = target
        self.new_body = new_body
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the substitute algorithm refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with substituted algorithm
        """
        self.source = source

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # If new_body is provided, replace the entire function body with it
        if self.new_body:
            return self._replace_with_new_body(tree, source)
        else:
            # Otherwise try to auto-transform the algorithm
            return self._auto_transform_algorithm(tree, source)

    def _replace_with_new_body(self, tree: ast.Module, source: str) -> str:
        """Replace function body with provided new_body."""
        # Find the target function
        target_func = self._find_function(tree)
        if not target_func is None:
            # Parse the new body to get AST nodes
            try:
                new_ast = ast.parse(self.new_body)
                new_body_stmts = new_ast.body

                # Replace the function body
                target_func.body = new_body_stmts

                # Return the modified source
                return ast.unparse(tree)
            except SyntaxError as e:
                raise ValueError(f"Invalid new_body: {e}")

        raise ValueError(f"Function '{self.target}' not found")

    def _auto_transform_algorithm(self, tree: ast.Module, source: str) -> str:
        """Automatically detect and transform specific algorithm patterns."""
        # Find the target function
        target_func = self._find_function(tree)
        if target_func is None:
            raise ValueError(f"Function '{self.target}' not found")

        # Check if this is the pattern: multiple if statements checking equality,
        # all returning the checked value
        if self._is_equality_chain_pattern(target_func):
            return self._transform_equality_chain(tree, target_func, source)

        # If no pattern matches, raise an error
        raise ValueError(f"Unable to automatically transform algorithm for '{self.target}'")

    def _find_function(self, tree: ast.Module):
        """Find the target function in the AST tree."""
        if "::" in self.target:
            # Qualified target (class::method)
            class_name, method_name = self.target.split("::", 1)
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == method_name:
                            return item
            return None
        else:
            # Simple function name
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == self.target:
                    return node
            return None

    def _is_equality_chain_pattern(self, func: ast.FunctionDef) -> bool:
        """Check if function matches the equality chain pattern."""
        # Pattern: for loop with multiple if statements checking equality
        if len(func.body) != 2:
            return False

        for_loop = func.body[0]
        return_stmt = func.body[1]

        if not isinstance(for_loop, ast.For):
            return False

        if not isinstance(return_stmt, ast.Return):
            return False

        # Check if all statements in the loop body are if statements checking equality
        for stmt in for_loop.body:
            if not isinstance(stmt, ast.If):
                return False

            # Check if it's a simple equality check with a return
            if not self._is_equality_return_pattern(stmt):
                return False

        return True

    def _is_equality_return_pattern(self, if_stmt: ast.If) -> bool:
        """Check if an if statement follows the pattern: if var == value: return value"""
        if not isinstance(if_stmt.test, ast.Compare):
            return False

        if len(if_stmt.body) != 1 or not isinstance(if_stmt.body[0], ast.Return):
            return False

        if if_stmt.orelse:
            return False

        return True

    def _transform_equality_chain(self, tree: ast.Module, func: ast.FunctionDef, source: str) -> str:
        """Transform equality chain pattern to use membership check."""
        # Extract the loop variable, candidates, and return value
        for_loop = func.body[0]
        loop_var = for_loop.target

        # Extract all the candidate values being checked
        candidates = []
        for stmt in for_loop.body:
            if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare):
                # Get the value being compared
                if stmt.test.ops and isinstance(stmt.test.ops[0], ast.Eq):
                    # Could be "person == 'Don'" or "'Don' == person"
                    comparators = stmt.test.comparators
                    if comparators:
                        candidate = comparators[0]
                        candidates.append(candidate)

        if not candidates:
            raise ValueError("Could not extract candidates from equality chain")

        # Create new function body:
        # candidates = [value1, value2, value3]
        # for person in people:
        #     if person in candidates:
        #         return person
        # return ""

        # Create the assignment: candidates = [...]
        candidates_list = ast.List(elts=candidates, ctx=ast.Load())
        candidates_assign = ast.Assign(
            targets=[ast.Name(id="candidates", ctx=ast.Store())],
            value=candidates_list
        )

        # Create new if body with membership check
        loop_var_name = loop_var.id if isinstance(loop_var, ast.Name) else str(loop_var)
        new_test = ast.Compare(
            left=ast.Name(id=loop_var_name, ctx=ast.Load()),
            ops=[ast.In()],
            comparators=[ast.Name(id="candidates", ctx=ast.Load())]
        )

        new_return = ast.Return(value=ast.Name(id=loop_var_name, ctx=ast.Load()))
        new_if = ast.If(test=new_test, body=[new_return], orelse=[])

        # Create new for loop
        new_for = ast.For(
            target=loop_var,
            iter=for_loop.iter,
            body=[new_if],
            orelse=[]
        )

        # Get the return statement from original function
        final_return = func.body[1]

        # Set new body
        func.body = [candidates_assign, new_for, final_return]

        # Fix missing location information for new nodes
        ast.fix_missing_locations(tree)

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
            return self._find_function(tree) is not None
        except SyntaxError:
            return False
