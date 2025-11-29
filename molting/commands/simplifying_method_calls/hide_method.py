"""Hide Method refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class HideMethodCommand(BaseCommand):
    """Make a public method private by prefixing with underscore.

    The Hide Method refactoring converts a public method into a private method
    when it is not used outside the class. This reduces the public interface
    of a class to only those methods that are truly needed by other classes,
    making the contract of the class clearer and improving encapsulation.

    **When to use:**
    - A public method is only called from within its own class
    - You want to reduce the surface area of a class's public API
    - You want to make it clear that a method is an internal implementation detail
    - Refactoring a method that was previously part of the public interface but
      is no longer needed by external clients

    **Example:**
    Before:
        class Calculator:
            def calculate_total(self, items):
                return self.apply_discount(sum(items))

            def apply_discount(self, amount):
                return amount * 0.9

    After:
        class Calculator:
            def calculate_total(self, items):
                return self._apply_discount(sum(items))

            def _apply_discount(self, amount):
                return amount * 0.9
    """

    name = "hide-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply hide-method refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        class_name, method_name = parse_target(target, expected_parts=2)

        # Validate that the method name doesn't already start with underscore
        if method_name.startswith("_"):
            raise ValueError(f"Method '{method_name}' is already private")

        # Create the new private method name
        new_method_name = f"_{method_name}"

        # Apply the transformation
        self.apply_libcst_transform(HideMethodTransformer, class_name, method_name, new_method_name)


class HideMethodTransformer(cst.CSTTransformer):
    """Transforms a class to hide a method by making it private."""

    def __init__(self, class_name: str, method_name: str, new_method_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to hide
            new_method_name: New private name for the method
        """
        self.class_name = class_name
        self.method_name = method_name
        self.new_method_name = new_method_name
        self.in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to track if we're in the target class."""
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition."""
        if original_node.name.value == self.class_name:
            self.in_target_class = False
        return updated_node

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Leave function definition and rename if it's the target method."""
        if self.in_target_class and original_node.name.value == self.method_name:
            return updated_node.with_changes(name=cst.Name(self.new_method_name))
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Leave call expression and update method calls."""
        if self.in_target_class and self._is_target_method_call(updated_node):
            # Update the method call to use the new private name
            new_func = updated_node.func.with_changes(attr=cst.Name(self.new_method_name))
            return updated_node.with_changes(func=new_func)
        return updated_node

    def _is_target_method_call(self, node: cst.Call) -> bool:
        """Check if a call node is a call to self.method_name().

        Args:
            node: The call node to check

        Returns:
            True if this is a call to the target method, False otherwise
        """
        if not isinstance(node.func, cst.Attribute):
            return False

        return (
            isinstance(node.func.value, cst.Name)
            and node.func.value.value == "self"
            and node.func.attr.value == self.method_name
        )


# Register the command
register_command(HideMethodCommand)
