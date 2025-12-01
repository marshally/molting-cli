"""AST validators for matching different SymbolContext patterns.

This module provides validators that check if a given AST node matches
a specific usage pattern (context) for a symbol. Each validator corresponds
to a SymbolContext enum value and implements pattern matching logic.
"""

from typing import Protocol

import libcst as cst

from molting.core.symbol_context import SymbolContext


class ContextValidator(Protocol):
    """Protocol for validators that match AST nodes against symbol patterns."""

    def matches(self, node: cst.CSTNode, symbol: str, on_object: str | None = None) -> bool:
        """Check if the node matches the pattern for this context.

        Args:
            node: The CST node to check
            symbol: The symbol name to match
            on_object: Optional object name that the symbol should be accessed on
                      (e.g., for "person.name", symbol="name", on_object="person")

        Returns:
            True if the node matches the pattern, False otherwise
        """
        ...


class AttributeAccessValidator:
    """Validates ATTRIBUTE_ACCESS context: obj.field"""

    def matches(self, node: cst.CSTNode, symbol: str, on_object: str | None = None) -> bool:
        """Check if node is an attribute access matching the pattern.

        Matches patterns like:
        - obj.field (when on_object="obj", symbol="field")
        - obj.field1.field2 (when symbol="field2", on_object can be None)

        Args:
            node: The CST node to check
            symbol: The attribute name to match
            on_object: Optional object name to check

        Returns:
            True if node matches the attribute access pattern
        """
        if not isinstance(node, cst.Attribute):
            return False

        # Check if the attribute name matches
        if node.attr.value != symbol:
            return False

        # If on_object is specified, verify the base object name
        if on_object is not None:
            # Get the leftmost name in the attribute chain
            base = node.value
            while isinstance(base, cst.Attribute):
                base = base.value

            if not isinstance(base, cst.Name) or base.value != on_object:
                return False

        return True


class MethodCallValidator:
    """Validates METHOD_CALL context: obj.method()"""

    def matches(self, node: cst.CSTNode, symbol: str, on_object: str | None = None) -> bool:
        """Check if node is a method call matching the pattern.

        Matches patterns like:
        - obj.method() (when on_object="obj", symbol="method")
        - obj.method(args) (when on_object="obj", symbol="method")

        Args:
            node: The CST node to check
            symbol: The method name to match
            on_object: Optional object name to check

        Returns:
            True if node matches the method call pattern
        """
        if not isinstance(node, cst.Call):
            return False

        # The function being called should be an attribute access
        if not isinstance(node.func, cst.Attribute):
            return False

        # Check if the method name matches
        if node.func.attr.value != symbol:
            return False

        # If on_object is specified, verify the base object name
        if on_object is not None:
            # Get the leftmost name in the attribute chain
            base = node.func.value
            while isinstance(base, cst.Attribute):
                base = base.value

            if not isinstance(base, cst.Name) or base.value != on_object:
                return False

        return True


class FunctionCallValidator:
    """Validates FUNCTION_CALL context: function()"""

    def matches(self, node: cst.CSTNode, symbol: str, on_object: str | None = None) -> bool:
        """Check if node is a function call matching the pattern.

        Matches patterns like:
        - function() (when symbol="function")
        - function(args) (when symbol="function")

        Args:
            node: The CST node to check
            symbol: The function name to match
            on_object: Should be None for function calls (not used)

        Returns:
            True if node matches the function call pattern
        """
        if not isinstance(node, cst.Call):
            return False

        # The function being called should be a simple name (not an attribute)
        if not isinstance(node.func, cst.Name):
            return False

        # Check if the function name matches
        return node.func.value == symbol


class AssignmentTargetValidator:
    """Validates ASSIGNMENT_TARGET context: x = value"""

    def matches(self, node: cst.CSTNode, symbol: str, on_object: str | None = None) -> bool:
        """Check if node is an assignment target matching the pattern.

        Args:
            node: The CST node to check
            symbol: The variable name to match
            on_object: Should be None for simple assignments (not used)

        Returns:
            True if node matches the assignment target pattern
        """
        if not isinstance(node, cst.Assign):
            return False

        # Check all assignment targets
        for target in node.targets:
            if isinstance(target.target, cst.Name) and target.target.value == symbol:
                return True

        return False


def get_validator(context: SymbolContext) -> ContextValidator:
    """Get the appropriate validator for a given context type.

    Args:
        context: The SymbolContext to get a validator for

    Returns:
        A ContextValidator instance for the given context

    Raises:
        NotImplementedError: If the context type doesn't have a validator yet
    """
    validators: dict[SymbolContext, ContextValidator] = {
        SymbolContext.ATTRIBUTE_ACCESS: AttributeAccessValidator(),
        SymbolContext.METHOD_CALL: MethodCallValidator(),
        SymbolContext.FUNCTION_CALL: FunctionCallValidator(),
        SymbolContext.ASSIGNMENT_TARGET: AssignmentTargetValidator(),
    }

    if context not in validators:
        raise NotImplementedError(f"Validator for {context.name} is not yet implemented")

    return validators[context]
