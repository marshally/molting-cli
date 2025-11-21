"""Introduce Foreign Method refactoring - add method to client class."""

import ast
import re
from pathlib import Path

from molting.core.refactoring_base import RefactoringBase


class IntroduceForeignMethod(RefactoringBase):
    """Add a method to the client class when you can't modify the server class."""

    def __init__(
        self,
        file_path: str,
        target: str,
        for_class: str,
        name: str,
    ):
        """Initialize the IntroduceForeignMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method with line number (e.g., "Report::generate#L6")
            for_class: The type name for the foreign method's first parameter (e.g., "date")
            name: Name of the new foreign method (e.g., "next_day")
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.target = target
        self.for_class = for_class
        self.method_name = name

    def apply(self, source: str) -> str:
        """Apply the introduce foreign method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with foreign method added
        """
        # Parse the target (ClassName::method_name#L{line})
        method_spec, target_line, _ = self.parse_line_range_target(self.target)
        class_name, method_name = self.parse_qualified_target(method_spec)

        # Parse the AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class and method
        target_class = self.find_class_def(tree, class_name)
        if target_class is None:
            raise ValueError(f"Class '{class_name}' not found")

        target_method = self.find_method_in_class(target_class, method_name)
        if target_method is None:
            raise ValueError(f"Method '{method_name}' not found in class '{class_name}'")

        # Get the lines of source code for extracting the target expression
        lines = source.splitlines(keepends=False)
        target_line_index = target_line - 1  # Convert to 0-indexed

        if target_line_index >= len(lines):
            raise ValueError(f"Line {target_line} not found in source code")

        # Find the expression to extract on the target line
        target_source_line = lines[target_line_index]

        # Extract the assignment variable name and expression
        if "=" not in target_source_line:
            raise ValueError(f"No assignment found on line {target_line}")

        eq_index = target_source_line.find("=")
        var_name = target_source_line[:eq_index].strip()
        expression = target_source_line[eq_index + 1 :].strip()

        # Get the parameter name (the first variable referenced in the expression)
        param_name = self._extract_param_name(expression)

        # Create the foreign method body
        # Replace the specific variable with 'arg' in the expression
        foreign_method_body = self._create_foreign_method_body(expression, param_name)

        # Find the statement in the method that corresponds to this line
        target_stmt = None
        for stmt in target_method.body:
            if hasattr(stmt, "lineno") and stmt.lineno == target_line:
                target_stmt = stmt
                break

        if target_stmt is None:
            raise ValueError(
                f"Could not find statement at line {target_line} in method {method_name}"
            )

        # Now modify the AST
        # 1. Replace the line in the target method
        self._replace_expression_in_stmt(target_stmt, var_name, param_name)

        # 2. Add the foreign method to the class
        self._add_foreign_method(target_class, target_method, foreign_method_body)

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
            method_spec, target_line, _ = self.parse_line_range_target(self.target)
            class_name, method_name = self.parse_qualified_target(method_spec)

            tree = ast.parse(source)

            target_class = self.find_class_def(tree, class_name)
            if target_class is None:
                return False

            target_method = self.find_method_in_class(target_class, method_name)
            if target_method is None:
                return False

            # Validate that the line exists
            lines = source.splitlines()
            if target_line - 1 >= len(lines):
                return False

            return True
        except Exception:
            return False

    def _extract_param_name(self, expression: str) -> str:
        """Extract the parameter name from the expression.

        Gets the first Name node that is accessed as an attribute
        (e.g., previous_end.year -> returns previous_end).

        Args:
            expression: The expression string

        Returns:
            The parameter name found
        """
        try:
            # Parse the expression as AST
            parsed = ast.parse(expression, mode="eval")

            # Find the first Name node that has attributes accessed on it
            # This prioritizes data sources (like previous_end) over type names (like date)
            for node in ast.walk(parsed):
                if isinstance(node, ast.Name):
                    # Skip if this is a built-in or module name that's used as a function
                    if node.id not in [
                        "date",
                        "datetime",
                        "timedelta",
                        "int",
                        "str",
                        "float",
                        "bool",
                        "list",
                        "dict",
                        "tuple",
                        "set",
                    ]:
                        return node.id

            # If all names are built-ins, find any Name node
            for node in ast.walk(parsed):
                if isinstance(node, ast.Name):
                    return node.id

        except Exception:
            pass

        # Fallback: regex-based extraction (prioritize names with dots)
        # Look for variable.attribute patterns
        match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)", expression)
        if match:
            return match.group(1)

        # If no attributes, extract first variable
        match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)", expression)
        if match:
            return match.group(1)

        return "arg"

    def _create_foreign_method_body(self, expression: str, param_name: str) -> str:
        """Create the body expression for the foreign method.

        Replace references to the parameter with 'arg'.

        Args:
            expression: The original expression
            param_name: The parameter name to replace with 'arg'

        Returns:
            The modified expression
        """
        # Use word boundaries to avoid replacing parts of larger names
        # Replace param_name with 'arg'
        pattern = r"\b" + re.escape(param_name) + r"\b"
        return re.sub(pattern, "arg", expression)

    def _replace_expression_in_stmt(
        self,
        stmt: ast.stmt,
        var_name: str,
        param_name: str,
    ) -> None:
        """Replace the expression with a call to the foreign method.

        Args:
            stmt: The statement containing the assignment
            var_name: The variable name on the left side of assignment
            param_name: The parameter name to pass to the foreign method
        """
        if isinstance(stmt, ast.Assign):
            # Check if this assignment targets the right variable
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    # Found it! Replace with a call
                    new_value = ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr=self.method_name,
                            ctx=ast.Load(),
                        ),
                        args=[ast.Name(id=param_name, ctx=ast.Load())],
                        keywords=[],
                    )
                    stmt.value = new_value
                    return

    def _add_foreign_method(
        self,
        class_node: ast.ClassDef,
        after_method: ast.FunctionDef,
        body_expression: str,
    ) -> None:
        """Add a foreign method to the class.

        Args:
            class_node: The ClassDef AST node
            after_method: The method to add the foreign method after
            body_expression: The expression body for the foreign method
        """
        # Parse the body expression
        try:
            expr_node = ast.parse(body_expression, mode="eval").body
        except SyntaxError as e:
            raise ValueError(f"Could not parse expression: {body_expression}") from e

        # Create the foreign method
        # def next_day(self, arg):
        #     # Foreign method for {for_class}
        #     return {body_expression}
        method_def = ast.FunctionDef(
            name=self.method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg="self", annotation=None),
                    ast.arg(arg="arg", annotation=None),
                ],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=[
                ast.Return(value=expr_node),
            ],
            decorator_list=[],
        )

        # Find the position to insert (after the target method)
        insert_position = len(class_node.body)
        for i, item in enumerate(class_node.body):
            if item is after_method:
                insert_position = i + 1
                break

        class_node.body.insert(insert_position, method_def)
