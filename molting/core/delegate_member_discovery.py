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
                        # Handle string annotations (forward references)
                        elif isinstance(annotation, cst.SimpleString):
                            # Remove quotes from "ClassName"
                            return annotation.value.strip('"').strip("'")

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
        members: list[DelegateMember] = []

        # Find the class in the module
        class_def = self._find_class(class_name)
        if class_def is None:
            return members

        # Enumerate fields from __init__
        members.extend(self._enumerate_fields(class_def))

        # Enumerate methods and properties
        members.extend(self._enumerate_methods_and_properties(class_def))

        return members

    def _find_class(self, class_name: str) -> cst.ClassDef | None:
        """Find a class definition by name in the module.

        Args:
            class_name: Name of the class to find

        Returns:
            The class definition or None if not found
        """
        for stmt in self.module.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == class_name:
                return stmt
        return None

    def _enumerate_fields(self, class_def: cst.ClassDef) -> list[DelegateMember]:
        """Enumerate all public fields from __init__.

        Args:
            class_def: The class definition to enumerate

        Returns:
            List of DelegateMember objects for public fields
        """
        fields: list[DelegateMember] = []

        if not isinstance(class_def.body, cst.IndentedBlock):
            return fields

        # Find __init__ method
        init_method = None
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                init_method = stmt
                break

        if init_method is None or not isinstance(init_method.body, cst.IndentedBlock):
            return fields

        # Collect all self.field = value assignments
        for stmt in init_method.body.body:
            if not isinstance(stmt, cst.SimpleStatementLine):
                continue

            for item in stmt.body:
                if not isinstance(item, cst.Assign):
                    continue

                for target in item.targets:
                    if not isinstance(target.target, cst.Attribute):
                        continue

                    # Check if this is self.field_name
                    if not (
                        isinstance(target.target.value, cst.Name)
                        and target.target.value.value == "self"
                    ):
                        continue

                    field_name = target.target.attr.value

                    # Skip private fields (starting with underscore)
                    if field_name.startswith("_"):
                        continue

                    # Add the field
                    fields.append(DelegateMember(name=field_name, kind="field", node=stmt))

        return fields

    def _enumerate_methods_and_properties(self, class_def: cst.ClassDef) -> list[DelegateMember]:
        """Enumerate all public methods and properties from a class.

        Args:
            class_def: The class definition to enumerate

        Returns:
            List of DelegateMember objects for public methods and properties
        """
        members: list[DelegateMember] = []

        if not isinstance(class_def.body, cst.IndentedBlock):
            return members

        # Track properties by name to detect setters/deleters
        properties: dict[str, DelegateMember] = {}

        # Enumerate all methods in the class
        for stmt in class_def.body.body:
            if not isinstance(stmt, cst.FunctionDef):
                continue

            method_name = stmt.name.value

            # Skip private methods (starting with underscore)
            if method_name.startswith("_"):
                continue

            # Check if this is a property, setter, or deleter
            is_property = False
            is_setter = False
            is_deleter = False

            for decorator in stmt.decorators:
                decorator_name = self._get_decorator_name(decorator)
                if decorator_name == "property":
                    is_property = True
                elif decorator_name.endswith(".setter"):
                    is_setter = True
                    # Extract property name from "property_name.setter"
                    method_name = decorator_name.split(".")[0]
                elif decorator_name.endswith(".deleter"):
                    is_deleter = True
                    # Extract property name from "property_name.deleter"
                    method_name = decorator_name.split(".")[0]

            if is_property:
                # This is a @property decorator
                member = DelegateMember(
                    name=method_name,
                    kind="property",
                    node=stmt,
                    has_setter=False,
                    has_deleter=False,
                )
                properties[method_name] = member
            elif is_setter:
                # This is a setter - update the existing property
                if method_name in properties:
                    properties[method_name].has_setter = True
            elif is_deleter:
                # This is a deleter - update the existing property
                if method_name in properties:
                    properties[method_name].has_deleter = True
            else:
                # This is a regular method
                members.append(DelegateMember(name=method_name, kind="method", node=stmt))

        # Add all properties to the members list
        members.extend(properties.values())

        return members

    def _get_decorator_name(self, decorator: cst.Decorator) -> str:
        """Extract the decorator name from a decorator node.

        Args:
            decorator: The decorator node

        Returns:
            The decorator name as a string (e.g., "property" or "name.setter")
        """
        decorator_expr = decorator.decorator

        # Simple decorator: @property
        if isinstance(decorator_expr, cst.Name):
            return decorator_expr.value

        # Attribute decorator: @name.setter
        if isinstance(decorator_expr, cst.Attribute):
            # Build the full attribute path
            parts = []
            current = decorator_expr
            while isinstance(current, cst.Attribute):
                parts.append(current.attr.value)
                current = current.value
            if isinstance(current, cst.Name):
                parts.append(current.value)
            return ".".join(reversed(parts))

        return ""

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
        if member.kind == "field":
            return self._generate_field_delegating_method(member, delegate_field)
        elif member.kind == "method":
            return self._generate_method_delegating_method(member, delegate_field)
        elif member.kind == "property":
            return self._generate_property_delegating_method(member, delegate_field)
        else:
            raise ValueError(f"Unknown member kind: {member.kind}")

    def _generate_field_delegating_method(
        self, member: DelegateMember, delegate_field: str
    ) -> cst.FunctionDef:
        """Generate a get_<field>() method for a field member.

        Args:
            member: The field member
            delegate_field: Name of the delegate field

        Returns:
            FunctionDef for get_<field>() method
        """
        from molting.core.code_generation_utils import create_parameter

        private_delegate = f"_{delegate_field}"

        # Create: return self._delegate.field
        return_stmt = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Attribute(
                        value=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name(private_delegate),
                        ),
                        attr=cst.Name(member.name),
                    )
                )
            ]
        )

        # Create: def get_<field>(self): return self._delegate.field
        return cst.FunctionDef(
            name=cst.Name(f"get_{member.name}"),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(body=[return_stmt]),
        )

    def _generate_method_delegating_method(
        self, member: DelegateMember, delegate_field: str
    ) -> cst.FunctionDef:
        """Generate a delegating method for a regular method member.

        Args:
            member: The method member
            delegate_field: Name of the delegate field

        Returns:
            FunctionDef for delegating method
        """
        from molting.core.code_generation_utils import create_parameter

        private_delegate = f"_{delegate_field}"

        # Create: return self._delegate.method()
        return_stmt = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(private_delegate),
                            ),
                            attr=cst.Name(member.name),
                        ),
                        args=[],
                    )
                )
            ]
        )

        # Create: def method(self): return self._delegate.method()
        return cst.FunctionDef(
            name=cst.Name(member.name),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(body=[return_stmt]),
        )

    def _generate_property_delegating_method(
        self, member: DelegateMember, delegate_field: str
    ) -> cst.FunctionDef:
        """Generate a @property delegating method for a property member.

        Args:
            member: The property member
            delegate_field: Name of the delegate field

        Returns:
            FunctionDef for @property delegating method
        """
        from molting.core.code_generation_utils import create_parameter

        private_delegate = f"_{delegate_field}"

        # Create: return self._delegate.property
        return_stmt = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Attribute(
                        value=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name(private_delegate),
                        ),
                        attr=cst.Name(member.name),
                    )
                )
            ]
        )

        # Create: @property def property(self): return self._delegate.property
        return cst.FunctionDef(
            name=cst.Name(member.name),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(body=[return_stmt]),
            decorators=[cst.Decorator(decorator=cst.Name("property"))],
        )

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
        # Get all public members of the delegate class
        members = self.enumerate_public_members(delegate_class)

        # Generate a delegating method for each member
        delegating_methods = []
        for member in members:
            method = self.generate_delegating_method(member, delegate_field)
            delegating_methods.append(method)

        return delegating_methods
