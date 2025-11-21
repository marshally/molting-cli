"""Base class for libcst transformers with class/method context tracking.

This module provides ClassAwareTransformer, a base class that extends libcst.CSTTransformer
to provide automatic tracking of class and method context during tree traversal.
"""

from typing import Optional
import libcst as cst


class ClassAwareTransformer(cst.CSTTransformer):
    """Base transformer that tracks class and method context during traversal.

    This transformer automatically tracks the current class context by implementing
    visit_ClassDef and leave_ClassDef methods. Subclasses can use the current_class
    attribute and matches_target() method to implement class/method-aware transformations.

    Attributes:
        class_name: Optional class name to match (None for module-level functions)
        function_name: Function or method name to match
        current_class: The name of the class currently being visited (None if at module level)
    """

    def __init__(self, class_name: Optional[str], function_name: str):
        """Initialize the transformer with target class and function names.

        Args:
            class_name: Optional class name if targeting a method. If None, targets
                       module-level functions.
            function_name: Name of the function or method to target.
        """
        self.class_name = class_name
        self.function_name = function_name
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when entering a class definition.

        Args:
            node: The ClassDef node being visited

        Returns:
            True to continue traversal
        """
        self.current_class = node.name.value
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Track when leaving a class definition.

        Args:
            original_node: The original ClassDef node
            updated_node: The updated ClassDef node

        Returns:
            The updated ClassDef node
        """
        self.current_class = None
        return updated_node

    def matches_target(self) -> bool:
        """Check if the current context matches the target class and function names.

        This method should be called from leave_FunctionDef (or similar) to determine
        if the current function/method being visited is the target.

        Returns:
            True if the current context matches the target class_name and function_name,
            False otherwise.
        """
        if self.class_name is None:
            # Looking for a module-level function
            # Don't match if we're inside a class
            if self.current_class is not None:
                return False
            return True

        # Looking for a class method
        # Only match if current_class matches the target
        if self.current_class != self.class_name:
            return False
        return True
