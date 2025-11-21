"""Base class for validation of class-aware refactorings using libcst."""

from typing import Optional
import libcst as cst


class ClassAwareValidator(cst.CSTVisitor):
    """Base class for validators that check if target classes/methods exist.

    This class provides common validation patterns for libcst-based refactorings
    that need to validate the existence of classes and methods before applying
    transformations.

    Attributes:
        class_name: Optional name of the target class, or None for module-level
        function_name: Name of the target function or method
        found: Whether the target class/method was found during traversal
        current_class: Name of the class currently being visited, or None
    """

    def __init__(self, class_name: Optional[str], function_name: str):
        """Initialize the validator.

        Args:
            class_name: Optional class name if targeting a method in a class.
                       Pass None for module-level functions.
            function_name: The name of the function or method to find.

        Raises:
            TypeError: If function_name is not a string.
        """
        if not isinstance(function_name, str):
            raise TypeError(f"function_name must be a string, got {type(function_name)}")

        self.class_name = class_name
        self.function_name = function_name
        self.found = False
        self.current_class = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """Track when entering a class definition.

        Args:
            node: The ClassDef node being visited.

        Returns:
            True to continue visiting child nodes.
        """
        self.current_class = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        """Track when leaving a class definition.

        Args:
            node: The ClassDef node being left.
        """
        self.current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Check if this function matches the target.

        This method checks both the function/method name and the current class
        context to determine if we've found the target function.

        Args:
            node: The FunctionDef node being visited.

        Returns:
            True to continue visiting child nodes.
        """
        func_name = node.name.value

        if self.class_name is None:
            # Looking for a module-level function
            if self.current_class is None and func_name == self.function_name:
                self.found = True
        else:
            # Looking for a method in a class
            if self.current_class == self.class_name and func_name == self.function_name:
                self.found = True

        return True
