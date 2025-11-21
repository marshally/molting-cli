"""Replace Method with Method Object refactoring - extract a method into its own class."""

import ast
import re
from pathlib import Path
from typing import List, Set

from molting.core.refactoring_base import RefactoringBase


class ReplaceMethodWithMethodObject(RefactoringBase):
    """Extract a long method into its own object (method object pattern).

    This refactoring transforms a method with many local variables into a
    dedicated class that encapsulates the computation, improving clarity for
    long or complex methods.
    """

    def __init__(self, file_path: str, target: str):
        """Initialize the ReplaceMethodWithMethodObject refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target specification (e.g., "Account::gamma")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

        # Parse the target specification to extract class and method names
        try:
            self.class_name, self.method_name = self.parse_qualified_target(self.target)
        except ValueError:
            raise ValueError(f"Invalid target format: {self.target}")

    def apply(self, source: str) -> str:
        """Apply the replace method with method object refactoring.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with method extracted to a method object
        """
        self.source = source

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class and method
        class_def = self.find_class_def(tree, self.class_name)
        if not class_def:
            raise ValueError(f"Class '{self.class_name}' not found in source code")

        method_def = self.find_method_in_class(class_def, self.method_name)
        if not method_def:
            raise ValueError(f"Method '{self.method_name}' not found in class '{self.class_name}'")

        # Find any helper methods called by this method (self._method_name calls)
        helper_methods = self._find_private_helper_methods(method_def, class_def)

        # Find any non-private methods called by this method
        non_private_methods = self._find_non_private_methods_called(method_def)

        # Apply the refactoring
        refactored_source = self._refactor_source(
            source, class_def, method_def, helper_methods, non_private_methods
        )

        return refactored_source

    def _find_private_helper_methods(
        self, method_def: ast.FunctionDef, class_def: ast.ClassDef
    ) -> Set[str]:
        """Find all private helper methods called by the given method.

        Only finds methods that start with underscore (private methods).

        Args:
            method_def: The method AST node
            class_def: The class AST node

        Returns:
            Set of private helper method names that are called
        """
        called_methods = set()

        # Find all method calls in the method body
        for node in ast.walk(method_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # This is a self.method_name() call
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                        method_name = node.func.attr
                        # Only include private methods (starting with _)
                        if method_name.startswith("_"):
                            called_methods.add(method_name)

        return called_methods

    def _find_non_private_methods_called(self, method_def: ast.FunctionDef) -> Set[str]:
        """Find all non-private methods called by the given method.

        Args:
            method_def: The method AST node

        Returns:
            Set of non-private method names that are called
        """
        called_methods = set()

        # Find all method calls in the method body
        for node in ast.walk(method_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # This is a self.method_name() call
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                        method_name = node.func.attr
                        # Only include non-private methods (not starting with _)
                        if not method_name.startswith("_"):
                            called_methods.add(method_name)

        return called_methods

    def _refactor_source(
        self,
        source: str,
        class_def: ast.ClassDef,
        method_def: ast.FunctionDef,
        helper_methods: Set[str],
        non_private_methods: Set[str],
    ) -> str:
        """Apply the refactoring using AST-based manipulation.

        Args:
            source: The source code
            class_def: The class AST node
            method_def: The method AST node
            helper_methods: Set of private helper method names
            non_private_methods: Set of non-private method names called

        Returns:
            Refactored source code
        """
        lines = source.split("\n")

        # Extract parameters and class name for method object
        params = self._extract_method_params(method_def)
        method_object_class_name = self.method_name.capitalize()

        # Extract original method body lines (without the def line)
        method_start_line = method_def.lineno - 1
        method_end_line = method_def.end_lineno or len(lines)
        method_body_lines = lines[method_start_line + 1 : method_end_line]

        # Create the replacement method that just delegates
        method_indent = len(lines[method_start_line]) - len(lines[method_start_line].lstrip())
        param_str = ", ".join(params)
        delegation_method = f"{' ' * method_indent}def {self.method_name}(self, {param_str}):\n"
        delegation_method += f"{' ' * (method_indent + 4)}return {method_object_class_name}(self, {param_str}).compute()"

        # Build the method object class code
        method_object_code = self._build_method_object_class(
            method_object_class_name,
            params,
            method_body_lines,
            class_def,
            helper_methods,
            non_private_methods,
            lines,
            method_indent,
        )

        # Build result: lines before method + delegation + lines after method
        result_lines = lines[:method_start_line]
        result_lines.extend(delegation_method.split("\n"))
        result_lines.extend(lines[method_end_line:])

        # Remove helper methods that we're moving to the method object
        # We need to find their positions and remove them
        helper_start_ends = []
        for helper_name in helper_methods:
            helper_method = self.find_method_in_class(class_def, helper_name)
            if helper_method and helper_method.end_lineno:
                h_start = helper_method.lineno - 1
                h_end = helper_method.end_lineno
                # Adjust for the changes to the method we just made
                size_delta = len(delegation_method.split("\n")) - (
                    method_end_line - method_start_line
                )
                h_start += size_delta
                h_end += size_delta
                helper_start_ends.append((h_start, h_end, helper_name))

        # Remove helper methods in reverse order (from end to start)
        helper_start_ends.sort(key=lambda x: x[0], reverse=True)
        for h_start, h_end, _ in helper_start_ends:
            del result_lines[h_start:h_end]

        # Insert the method object class at the end of the source
        result_lines.append("")
        result_lines.append("")
        result_lines.extend(method_object_code.rstrip("\n").split("\n"))

        return "\n".join(result_lines)

    def _build_method_object_class(
        self,
        class_name: str,
        params: List[str],
        method_body_lines: List[str],
        class_def: ast.ClassDef,
        helper_methods: Set[str],
        non_private_methods: Set[str],
        source_lines: List[str],
        base_indent: int,
    ) -> str:
        """Build the method object class code.

        Args:
            class_name: Name of the method object class
            params: List of parameter names
            method_body_lines: The method body lines (excluding def line)
            class_def: The original class definition
            helper_methods: Set of private helper method names
            non_private_methods: Set of non-private method names called
            source_lines: All source lines
            base_indent: The base indentation level

        Returns:
            The method object class code
        """
        # Determine the original indentation of method body
        first_body_line = None
        for line in method_body_lines:
            if line.strip():
                first_body_line = line
                break

        if first_body_line:
            original_indent = len(first_body_line) - len(first_body_line.lstrip())
        else:
            original_indent = base_indent + 4

        # Transform the method body for the method object
        compute_body = []
        for line in method_body_lines:
            if not line.strip():
                compute_body.append("")
            else:
                # Remove the original indentation
                dedented = line[original_indent:] if len(line) > original_indent else line.lstrip()

                # Replace parameter names with self.parameter
                for param in params:
                    pattern = r"\b" + re.escape(param) + r"\b"
                    dedented = re.sub(pattern, f"self.{param}", dedented)

                # Replace non-private self.method() calls with self.account.method()
                for non_private in non_private_methods:
                    pattern = r"\bself\." + re.escape(non_private) + r"\("
                    replacement = r"self.account." + non_private + "("
                    dedented = re.sub(pattern, replacement, dedented)

                # Add proper indentation for method object class
                indented_line = "        " + dedented
                compute_body.append(indented_line)

        # Build the class
        class_lines = []
        class_lines.append(f"class {class_name}:")
        class_lines.append(f'    def __init__(self, account, {", ".join(params)}):')
        class_lines.append("        self.account = account")
        for param in params:
            class_lines.append(f"        self.{param} = {param}")
        class_lines.append("")
        class_lines.append("    def compute(self):")

        # Add the compute method body
        if compute_body:
            class_lines.extend(compute_body)
        else:
            class_lines.append("        pass")

        # Add helper methods
        for helper_name in sorted(helper_methods):
            helper_method = self.find_method_in_class(class_def, helper_name)
            if helper_method:
                h_start = helper_method.lineno - 1
                h_end = helper_method.end_lineno
                helper_lines = source_lines[h_start:h_end]

                # Determine indentation of original helper
                orig_h_indent = None
                for line in helper_lines:
                    if line.strip():
                        orig_h_indent = len(line) - len(line.lstrip())
                        break

                if orig_h_indent is None:
                    orig_h_indent = base_indent + 4

                # Add blank line before helper
                class_lines.append("")

                # Add helper method with proper indentation for the method object class
                for line in helper_lines:
                    if not line.strip():
                        class_lines.append("")
                    else:
                        dedented = (
                            line[orig_h_indent:] if len(line) > orig_h_indent else line.lstrip()
                        )
                        indented = "    " + dedented  # 4 spaces for class method
                        class_lines.append(indented)

        return "\n".join(class_lines) + "\n"

    def _extract_method_params(self, method_def: ast.FunctionDef) -> List[str]:
        """Extract parameter names from a method definition.

        Args:
            method_def: The AST FunctionDef node

        Returns:
            List of parameter names (excluding 'self')
        """
        params = []
        for arg in method_def.args.args:
            if arg.arg != "self":
                params.append(arg.arg)
        return params

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)
            class_def = self.find_class_def(tree, self.class_name)
            if not class_def:
                return False
            method_def = self.find_method_in_class(class_def, self.method_name)
            return method_def is not None
        except SyntaxError:
            return False
