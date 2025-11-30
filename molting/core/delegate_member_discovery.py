"""Utility for discovering and generating delegating methods for hide-delegate refactoring."""

from dataclasses import dataclass
from typing import Literal

import libcst as cst


@dataclass
class DelegateMember:
    """Represents a member (field, method, or property) of a delegate class.

    Attributes:
        name: The member name
        kind: Type of member (field, method, or property)
        node: The CST node representing this member
        has_setter: For properties, whether a setter is defined
        has_deleter: For properties, whether a deleter is defined
    """

    name: str
    kind: Literal["field", "method", "property"]
    node: cst.FunctionDef | cst.SimpleStatementLine
    has_setter: bool = False
    has_deleter: bool = False


class DelegateMemberDiscovery:
    """Discovers public members of a delegate class for hide-delegate refactoring.

    This utility helps implement the Hide Delegate pattern by:
    1. Finding the delegate class from a field's type annotation
    2. Enumerating all public members (fields, methods, properties) of the delegate
    3. Generating delegating methods for each member

    Example:
        module = cst.parse_module(source_code)
        discovery = DelegateMemberDiscovery(module)

        # Find what class the 'compensation' field delegates to
        delegate_class = discovery.find_delegate_class("Employee", "compensation")
        # Returns: "Compensation"

        # Get all public members of Compensation class
        members = discovery.enumerate_public_members("Compensation")
        # Returns: [DelegateMember(name="salary", kind="field", ...),
        #           DelegateMember(name="calculate_pay", kind="method", ...), ...]

        # Generate delegating methods for all members
        methods = discovery.generate_all_delegating_methods("Compensation", "compensation")
    """

    def __init__(self, module: cst.Module) -> None:
        """Initialize the discovery utility.

        Args:
            module: The CST module to analyze
        """
        self.module = module

    def find_delegate_class(self, server_class: str, delegate_field: str) -> str | None:
        """Find the class type of a delegate field from __init__ parameter type hints.

        Analyzes the __init__ method of the server class to find what type the
        delegate field is assigned from. Currently supports type-hinted parameters.

        Args:
            server_class: Name of the class containing the delegate field
            delegate_field: Name of the field to find the type for

        Returns:
            Name of the delegate class, or None if not found or no type hint available

        Example:
            # Given:
            class Employee:
                def __init__(self, compensation: Compensation):
                    self.compensation = compensation

            # Returns: "Compensation"
        """
        # Find the server class in the module
        for stmt in self.module.body:
            if not isinstance(stmt, cst.ClassDef):
                continue
            if stmt.name.value != server_class:
                continue

            # Find __init__ method
            if not isinstance(stmt.body, cst.IndentedBlock):
                continue

            for class_stmt in stmt.body.body:
                if not isinstance(class_stmt, cst.FunctionDef):
                    continue
                if class_stmt.name.value != "__init__":
                    continue

                # Look through parameters for type hints
                for param in class_stmt.params.params:
                    # Skip 'self' parameter
                    if param.name.value == "self":
                        continue

                    # Check if this parameter is assigned to our delegate field
                    # by looking at the __init__ body
                    assigns_to_field = self._parameter_assigns_to_field(
                        class_stmt, param.name.value, delegate_field
                    )

                    if assigns_to_field and param.annotation is not None:
                        # Extract type from annotation
                        annotation = param.annotation.annotation
                        if isinstance(annotation, cst.Name):
                            return annotation.value

        return None

    def _parameter_assigns_to_field(
        self, init_method: cst.FunctionDef, param_name: str, field_name: str
    ) -> bool:
        """Check if a parameter is assigned to a specific field in __init__.

        Args:
            init_method: The __init__ method to check
            param_name: Name of the parameter
            field_name: Name of the field

        Returns:
            True if there's an assignment like self.field_name = param_name
        """
        if not isinstance(init_method.body, cst.IndentedBlock):
            return False

        for stmt in init_method.body.body:
            if not isinstance(stmt, cst.SimpleStatementLine):
                continue

            for item in stmt.body:
                if not isinstance(item, cst.Assign):
                    continue

                # Check if this is self.field_name = param_name
                for target in item.targets:
                    if not isinstance(target.target, cst.Attribute):
                        continue

                    # Check target is self.field_name
                    if not (
                        isinstance(target.target.value, cst.Name)
                        and target.target.value.value == "self"
                        and target.target.attr.value == field_name
                    ):
                        continue

                    # Check value is param_name
                    if isinstance(item.value, cst.Name) and item.value.value == param_name:
                        return True

        return False

    def enumerate_public_members(self, class_name: str) -> list[DelegateMember]:
        """Get all public fields, methods, and properties of a class.

        Args:
            class_name: Name of the class to enumerate

        Returns:
            List of DelegateMember objects for all public members
        """
        # Placeholder - will implement in subsequent TDD cycles
        return []

    def generate_delegating_method(
        self, member: DelegateMember, delegate_field: str
    ) -> cst.FunctionDef:
        """Generate a delegating method for a single member.

        For fields: Creates get_<field>() -> return self._delegate.field
        For methods: Creates <method>(*args) -> return self._delegate.method(*args)
        For properties: Creates @property <name> -> return self._delegate.name

        Args:
            member: The member to generate a delegating method for
            delegate_field: Name of the delegate field (will be made private with _)

        Returns:
            The generated delegating method as a FunctionDef node
        """
        # Placeholder - will implement in subsequent TDD cycles
        raise NotImplementedError()

    def generate_all_delegating_methods(
        self, delegate_class: str, delegate_field: str
    ) -> list[cst.FunctionDef]:
        """Generate delegating methods for all public members of delegate class.

        Args:
            delegate_class: Name of the delegate class
            delegate_field: Name of the delegate field

        Returns:
            List of generated delegating methods
        """
        # Placeholder - will implement in subsequent TDD cycles
        return []
