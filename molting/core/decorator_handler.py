"""Decorator handling utilities for AST transformations.

This module provides utilities for managing decorators when transforming methods,
particularly for preserving method decorators during refactorings like extract method.

Key patterns:
- Decorators like @property, @staticmethod, @classmethod should be preserved on
  the original method when it's transformed
- New extracted helper methods should NOT inherit decorators (they're plain methods)
- When creating delegation methods, special decorators like @property can be
  applied to the delegation method
"""

import libcst as cst


class DecoratorHandler:
    """Manages decorators when transforming methods.

    Usage example:
        handler = DecoratorHandler(original_method)
        decorators = handler.get_decorators()
        new_method = create_new_helper_method()
        # Don't apply decorators to new method (it should be plain)
        # But preserve them on the original method if needed
        transformed = handler.apply_decorators(updated_original_method)
    """

    # Decorators that should be preserved on transformed methods
    PRESERVABLE_DECORATORS = {"property", "staticmethod", "classmethod"}

    def __init__(self, method: cst.FunctionDef) -> None:
        """Initialize handler with a method definition.

        Args:
            method: The function definition to extract decorators from
        """
        self.method = method

    def get_decorators(self) -> tuple[cst.Decorator, ...]:
        """Get all decorators from the method.

        Returns:
            Tuple of Decorator nodes
        """
        return self.method.decorators

    def should_preserve_decorator(self, decorator_name: str) -> bool:
        """Check if a decorator should be preserved during transformation.

        Args:
            decorator_name: Name of the decorator (e.g., "property")

        Returns:
            True if the decorator should be preserved
        """
        return decorator_name in self.PRESERVABLE_DECORATORS

    def has_preservable_decorators(self) -> bool:
        """Check if method has any decorators that should be preserved.

        Returns:
            True if method has at least one preservable decorator
        """
        for decorator in self.method.decorators:
            if self._extract_decorator_name(decorator) in self.PRESERVABLE_DECORATORS:
                return True
        return False

    def apply_decorators(self, target_method: cst.FunctionDef) -> cst.FunctionDef:
        """Apply decorators from this handler's method to a target method.

        Only applies decorators that should be preserved. Used when transforming
        methods where we want to keep the original decorators.

        Args:
            target_method: The method to apply decorators to

        Returns:
            The target method with decorators applied
        """
        # Only apply decorators that should be preserved
        preservable = tuple(
            d for d in self.method.decorators
            if self._extract_decorator_name(d) in self.PRESERVABLE_DECORATORS
        )

        return target_method.with_changes(decorators=preservable)

    def create_undecorated_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Create an undecorated version of a method.

        Used when creating helper methods that should not have decorators.

        Args:
            method: The method to strip decorators from

        Returns:
            The method with no decorators
        """
        return method.with_changes(decorators=())

    @staticmethod
    def _extract_decorator_name(decorator: cst.Decorator) -> str:
        """Extract the name of a decorator.

        Handles simple decorators like @property and complex ones like
        @some_module.decorator.

        Args:
            decorator: The decorator node

        Returns:
            The decorator name, or empty string if can't be extracted
        """
        if isinstance(decorator.decorator, cst.Name):
            return decorator.decorator.value
        elif isinstance(decorator.decorator, cst.Attribute):
            # Handle @module.decorator patterns
            if isinstance(decorator.decorator.attr, cst.Name):
                return decorator.decorator.attr.value
        elif isinstance(decorator.decorator, cst.Call):
            # Handle @decorator(...) patterns
            if isinstance(decorator.decorator.func, cst.Name):
                return decorator.decorator.func.value
            elif isinstance(decorator.decorator.func, cst.Attribute):
                if isinstance(decorator.decorator.func.attr, cst.Name):
                    return decorator.decorator.func.attr.value
        return ""

    @staticmethod
    def copy_preservable_decorators_between_methods(
        source_method: cst.FunctionDef, target_method: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Copy preservable decorators from source method to target method.

        Convenience method that creates a handler from source and applies to target.

        Args:
            source_method: The method to copy decorators from
            target_method: The method to apply decorators to

        Returns:
            The target method with preservable decorators from source
        """
        handler = DecoratorHandler(source_method)
        return handler.apply_decorators(target_method)
