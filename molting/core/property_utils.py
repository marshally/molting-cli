"""Utilities for handling @property decorated methods."""

from dataclasses import dataclass

import libcst as cst


@dataclass
class PropertyDefinition:
    """Represents a property with its getter, setter, and deleter methods."""

    name: str
    getter: cst.FunctionDef
    setter: cst.FunctionDef | None
    deleter: cst.FunctionDef | None


class PropertyMethodHandler:
    """Handler for working with @property decorated method groups."""

    def __init__(self, module: cst.Module) -> None:
        """Initialize the handler with a module.

        Args:
            module: The module to analyze
        """
        self.module = module

    def is_property_method(self, method: cst.FunctionDef) -> bool:
        """Check if a method is part of a property definition.

        Args:
            method: The method to check

        Returns:
            True if the method has @property, @name.setter, or @name.deleter decorator
        """
        for decorator in method.decorators:
            if isinstance(decorator.decorator, cst.Name):
                # @property
                if decorator.decorator.value == "property":
                    return True
            elif isinstance(decorator.decorator, cst.Attribute):
                # @name.setter or @name.deleter
                attr_name = decorator.decorator.attr.value
                if attr_name in ("setter", "deleter"):
                    return True
        return False

    def find_properties_in_class(self, class_name: str) -> list[PropertyDefinition]:
        """Find all @property definitions in a class.

        Args:
            class_name: Name of the class to search

        Returns:
            List of PropertyDefinition objects
        """
        # Find the class
        class_def = None
        for node in self.module.body:
            if isinstance(node, cst.ClassDef) and node.name.value == class_name:
                class_def = node
                break

        if not class_def:
            return []

        # Group methods by property name
        property_groups: dict[str, dict[str, cst.FunctionDef]] = {}

        for stmt in class_def.body.body:
            if not isinstance(stmt, cst.FunctionDef):
                continue

            method_name = stmt.name.value
            decorator_type = self._get_property_decorator_type(stmt)

            if decorator_type == "property":
                if method_name not in property_groups:
                    property_groups[method_name] = {}
                property_groups[method_name]["getter"] = stmt
            elif decorator_type == "setter":
                if method_name not in property_groups:
                    property_groups[method_name] = {}
                property_groups[method_name]["setter"] = stmt
            elif decorator_type == "deleter":
                if method_name not in property_groups:
                    property_groups[method_name] = {}
                property_groups[method_name]["deleter"] = stmt

        # Convert to PropertyDefinition objects
        properties = []
        for prop_name, methods in property_groups.items():
            properties.append(
                PropertyDefinition(
                    name=prop_name,
                    getter=methods.get("getter"),  # type: ignore[arg-type]
                    setter=methods.get("setter"),
                    deleter=methods.get("deleter"),
                )
            )

        return properties

    def _get_property_decorator_type(self, method: cst.FunctionDef) -> str | None:
        """Get the type of property decorator on a method.

        Args:
            method: The method to check

        Returns:
            "property", "setter", "deleter", or None
        """
        for decorator in method.decorators:
            if isinstance(decorator.decorator, cst.Name):
                if decorator.decorator.value == "property":
                    return "property"
            elif isinstance(decorator.decorator, cst.Attribute):
                attr_name = decorator.decorator.attr.value
                if attr_name in ("setter", "deleter"):
                    return attr_name
        return None

    def get_property_group(self, method_name: str, class_name: str) -> PropertyDefinition | None:
        """Get the full property group (getter/setter/deleter) for a property name.

        Args:
            method_name: Name of the property
            class_name: Name of the class containing the property

        Returns:
            PropertyDefinition if found, None otherwise
        """
        properties = self.find_properties_in_class(class_name)
        for prop in properties:
            if prop.name == method_name:
                return prop
        return None

    def remove_property_from_class(
        self, class_def: cst.ClassDef, property_name: str
    ) -> cst.ClassDef:
        """Remove all methods for a property from a class.

        Args:
            class_def: The class to modify
            property_name: Name of the property to remove

        Returns:
            Modified class definition
        """
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            # Keep non-function statements
            if not isinstance(stmt, cst.FunctionDef):
                new_body_stmts.append(stmt)
                continue

            # Check if this is part of the property to remove
            if stmt.name.value == property_name and self.is_property_method(stmt):
                continue  # Skip this method

            new_body_stmts.append(stmt)

        # If class becomes empty, add pass
        if not new_body_stmts:
            new_body_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return class_def.with_changes(body=class_def.body.with_changes(body=tuple(new_body_stmts)))

    def add_property_to_class(
        self, class_def: cst.ClassDef, prop: PropertyDefinition
    ) -> cst.ClassDef:
        """Add all methods for a property to a class.

        Args:
            class_def: The class to modify
            prop: The property definition to add

        Returns:
            Modified class definition
        """
        new_body_stmts: list[cst.BaseStatement] = []

        # Remove any existing pass statements since we're adding real content
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Skip pass statements
                if any(isinstance(b, cst.Pass) for b in stmt.body):
                    continue
            new_body_stmts.append(stmt)

        # Add the property methods
        if prop.getter:
            new_body_stmts.append(prop.getter)
        if prop.setter:
            new_body_stmts.append(prop.setter)
        if prop.deleter:
            new_body_stmts.append(prop.deleter)

        return class_def.with_changes(body=class_def.body.with_changes(body=tuple(new_body_stmts)))
