"""Call site updater utility for updating method and constructor calls.

This module provides utilities to find and update all call sites throughout a module
when transformers modify method signatures, create new methods, or add factory functions.
"""

from typing import Optional

import libcst as cst


class AttributeCallReplacer(cst.CSTTransformer):
    """Visitor that replaces specific attribute and constructor calls.

    Handles two main patterns:
    1. Attribute delegation: obj.delegate.method() -> obj.new_method()
    2. Constructor to factory: ClassName(...) -> factory_name(...)
    """

    def __init__(
        self,
        object_name: Optional[str] = None,
        old_attr: Optional[str] = None,
        new_method: Optional[str] = None,
        nested_attr: Optional[str] = None,
        class_name: Optional[str] = None,
        factory_name: Optional[str] = None,
    ) -> None:
        """Initialize the replacer.

        Args:
            object_name: Name of the object for attribute delegation (e.g., 'person')
            old_attr: Name of the delegate field (e.g., 'department')
            new_method: Name of the new method to call (e.g., 'get_manager')
            nested_attr: Optional nested attribute access (e.g., 'manager')
            class_name: Name of class for constructor replacement (e.g., 'Employee')
            factory_name: Name of factory function (e.g., 'create_employee')
        """
        self.object_name = object_name
        self.old_attr = old_attr
        self.new_method = new_method
        self.nested_attr = nested_attr
        self.class_name = class_name
        self.factory_name = factory_name

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        """Replace nested attribute access patterns.

        Handles patterns like: obj.delegate.method -> obj.new_method()
        """
        # Check for obj.delegate.nested_attr pattern
        if (
            self.nested_attr
            and isinstance(updated_node.value, cst.Attribute)
            and isinstance(updated_node.value.value, cst.Name)
            and updated_node.value.attr.value == self.old_attr
            and updated_node.attr.value == self.nested_attr
        ):
            # Extract the object name from the pattern
            obj_name = updated_node.value.value.value
            # Only proceed if object_name matches (if specified) or always (if None)
            if self.object_name is None or obj_name == self.object_name:
                # Return obj.new_method() as a call
                return cst.Call(
                    func=cst.Attribute(
                        value=cst.Name(obj_name), attr=cst.Name(self.new_method)
                    )
                )

        return updated_node

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Replace constructor calls and method calls.

        Handles:
        1. ClassName(...) -> factory_name(...)
        2. obj.old_method(...) -> obj.new_method(...)
        """
        # Pattern 1: Constructor replacement
        if (
            self.class_name
            and self.factory_name
            and isinstance(updated_node.func, cst.Name)
            and updated_node.func.value == self.class_name
        ):
            # Replace Employee(...) with create_employee(...)
            return updated_node.with_changes(func=cst.Name(self.factory_name))

        # Pattern 2: Method call replacement (for simple cases)
        if (
            self.object_name
            and self.old_attr
            and self.new_method
            and not self.nested_attr
            and isinstance(updated_node.func, cst.Attribute)
            and isinstance(updated_node.func.value, cst.Name)
            and updated_node.func.value.value == self.object_name
            and updated_node.func.attr.value == self.old_attr
        ):
            # Replace person.get_department() with person.get_manager()
            return updated_node.with_changes(
                func=cst.Attribute(
                    value=cst.Name(self.object_name), attr=cst.Name(self.new_method)
                )
            )

        return updated_node


class CallSiteUpdater(cst.CSTTransformer):
    """Main visitor for updating all call sites in a module.

    This transformer finds and updates all occurrences of:
    - Attribute access patterns (obj.delegate.method -> obj.new_method)
    - Constructor calls (ClassName(...) -> factory_name(...))
    """

    def __init__(
        self,
        object_name: Optional[str] = None,
        old_attr: Optional[str] = None,
        new_method: Optional[str] = None,
        nested_attr: Optional[str] = None,
        class_name: Optional[str] = None,
        factory_name: Optional[str] = None,
    ) -> None:
        """Initialize the updater.

        Args:
            object_name: Name of the object for attribute delegation
            old_attr: Name of the delegate field
            new_method: Name of the new method to call
            nested_attr: Optional nested attribute access
            class_name: Name of class for constructor replacement
            factory_name: Name of factory function
        """
        self.replacer = AttributeCallReplacer(
            object_name=object_name,
            old_attr=old_attr,
            new_method=new_method,
            nested_attr=nested_attr,
            class_name=class_name,
            factory_name=factory_name,
        )

    def visit_Module(self, node: cst.Module) -> None:  # noqa: N802
        """Visit the module and apply replacements."""
        pass

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.BaseExpression:
        """Delegate to replacer for attribute updates."""
        return self.replacer.leave_Attribute(original_node, updated_node)

    def leave_Call(  # noqa: N802
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.BaseExpression:
        """Delegate to replacer for call updates."""
        return self.replacer.leave_Call(original_node, updated_node)
