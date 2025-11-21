"""Base classes for refactoring operations."""

import ast
import re
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple


class RefactoringBase(ABC):
    """Base class for all refactoring operations."""

    @abstractmethod
    def apply(self, source: str) -> str:
        """Apply the refactoring to the given source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code
        """
        pass

    @abstractmethod
    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        pass

    def parse_qualified_target(self, target: str) -> Tuple[str, str]:
        """Parse a qualified target in 'ClassName::method_name' format.

        Args:
            target: Target specification in the format 'ClassName::method_name'

        Returns:
            A tuple of (class_name, method_name)

        Example:
            >>> parse_qualified_target("MyClass::my_method")
            ("MyClass", "my_method")
        """
        parts = target.split("::", 1)
        class_name = parts[0]
        method_name = parts[1] if len(parts) > 1 else ""
        return class_name, method_name

    def parse_line_range_target(self, target: str) -> Tuple[str, int, int]:
        """Parse target specification with line range information.

        Parses targets like:
        - "Order::print_owing#L9-L11" -> class/method + start and end line
        - "Order::print_owing#L9" -> class/method + single line (start == end)
        - "calculate#L5-L7" -> function + line range
        - "function#L5" -> function + single line

        Args:
            target: Target specification string

        Returns:
            Tuple of (method_spec, start_line, end_line)

        Raises:
            ValueError: If target format is invalid
        """
        # Pattern: optional_class::optional_method#L{start}-L{end} or #L{start}
        pattern = r'^(.+?)#L(\d+)(?:-L(\d+))?$'
        match = re.match(pattern, target)

        if not match:
            raise ValueError(f"Invalid target format: {target}")

        method_spec = match.group(1)  # e.g., "Order::print_owing" or "calculate"
        start_line = int(match.group(2))
        end_line = int(match.group(3)) if match.group(3) else start_line

        return method_spec, start_line, end_line

    def find_class_def(self, tree: ast.Module, class_name: str) -> Optional[ast.ClassDef]:
        """Find a class definition in the AST by class name.

        Args:
            tree: The AST module
            class_name: Name of the class to find

        Returns:
            The ClassDef node if found, None otherwise
        """
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
        return None

    def find_method_in_class(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method in a class by method name.

        Args:
            class_node: The ClassDef node
            method_name: Name of the method to find

        Returns:
            The FunctionDef node if found, None otherwise
        """
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == method_name:
                return item
        return None

    def calculate_qualified_offset(
        self, source: str, class_name: str, method_name: str
    ) -> int:
        """Calculate byte offset for a qualified class::method target.

        Finds the byte offset in the source code where a method name appears
        within a specific class. This is useful for tools like rope that require
        an offset to identify the target for refactoring.

        Args:
            source: Python source code
            class_name: Name of the class containing the method
            method_name: Name of the method to find

        Returns:
            Byte offset of the method name in the source code

        Raises:
            ValueError: If class not found, method not found, or syntax error
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the class definition - only look at top-level classes
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Find the method in the class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        # Calculate offset from line and column numbers
                        lines = source.split('\n')
                        offset = 0

                        # Sum up bytes from all previous lines
                        for i, line in enumerate(lines):
                            if i < item.lineno - 1:
                                offset += len(line) + 1  # +1 for newline character
                            else:
                                # Found the line with the method definition
                                # Find the method name in this line
                                col_offset = line.find(method_name)
                                if col_offset != -1:
                                    return offset + col_offset
                                break

                        raise ValueError(f"Could not find offset for {method_name}")

                raise ValueError(
                    f"Method '{method_name}' not found in class '{class_name}'"
                )

        raise ValueError(f"Class '{class_name}' not found in source code")
