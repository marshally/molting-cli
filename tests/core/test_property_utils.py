"""Tests for PropertyMethodHandler utility."""

import libcst as cst
import pytest

from molting.core.property_utils import PropertyDefinition, PropertyMethodHandler


class TestPropertyDefinition:
    """Tests for PropertyDefinition dataclass."""

    def test_property_definition_creation(self) -> None:
        """Test that PropertyDefinition can be created with all fields."""
        # Create a simple getter method
        getter = cst.parse_module("@property\ndef name(self): pass").body[0]
        setter = cst.parse_module("@name.setter\ndef name(self, value): pass").body[0]

        prop_def = PropertyDefinition(
            name="test_property",
            getter=getter,
            setter=setter,
            deleter=None
        )

        assert prop_def.name == "test_property"
        assert prop_def.getter is not None
        assert prop_def.setter is not None
        assert prop_def.deleter is None


class TestPropertyMethodHandler:
    """Tests for PropertyMethodHandler."""

    def test_is_property_method_with_property_decorator(self) -> None:
        """Test identifying a method with @property decorator."""
        source = """
class Foo:
    @property
    def name(self):
        return self._name
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        class_def = module.body[0]
        method = class_def.body.body[0]

        assert handler.is_property_method(method) is True

    def test_is_property_method_with_setter_decorator(self) -> None:
        """Test identifying a method with @name.setter decorator."""
        source = """
class Foo:
    @name.setter
    def name(self, value):
        self._name = value
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        class_def = module.body[0]
        method = class_def.body.body[0]

        assert handler.is_property_method(method) is True

    def test_is_property_method_with_deleter_decorator(self) -> None:
        """Test identifying a method with @name.deleter decorator."""
        source = """
class Foo:
    @name.deleter
    def name(self):
        del self._name
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        class_def = module.body[0]
        method = class_def.body.body[0]

        assert handler.is_property_method(method) is True

    def test_is_property_method_with_regular_method(self) -> None:
        """Test that regular methods are not identified as property methods."""
        source = """
class Foo:
    def regular_method(self):
        pass
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        class_def = module.body[0]
        method = class_def.body.body[0]

        assert handler.is_property_method(method) is False

    def test_find_properties_in_class_with_getter_and_setter(self) -> None:
        """Test finding properties with both getter and setter."""
        source = """
class Employee:
    @property
    def sales_target(self):
        return self._sales_target

    @sales_target.setter
    def sales_target(self, value):
        self._sales_target = value
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        properties = handler.find_properties_in_class("Employee")

        assert len(properties) == 1
        assert properties[0].name == "sales_target"
        assert properties[0].getter is not None
        assert properties[0].setter is not None
        assert properties[0].deleter is None

    def test_find_properties_in_class_with_getter_only(self) -> None:
        """Test finding properties with only getter."""
        source = """
class Employee:
    @property
    def name(self):
        return self._name
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        properties = handler.find_properties_in_class("Employee")

        assert len(properties) == 1
        assert properties[0].name == "name"
        assert properties[0].getter is not None
        assert properties[0].setter is None
        assert properties[0].deleter is None

    def test_find_properties_in_class_with_multiple_properties(self) -> None:
        """Test finding multiple properties in a class."""
        source = """
class Employee:
    @property
    def name(self):
        return self._name

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        self._age = value
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        properties = handler.find_properties_in_class("Employee")

        assert len(properties) == 2
        property_names = {p.name for p in properties}
        assert property_names == {"name", "age"}

    def test_get_property_group(self) -> None:
        """Test getting full property group by name."""
        source = """
class Employee:
    @property
    def sales_target(self):
        return self._sales_target

    @sales_target.setter
    def sales_target(self, value):
        self._sales_target = value
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        prop = handler.get_property_group("sales_target", "Employee")

        assert prop is not None
        assert prop.name == "sales_target"
        assert prop.getter is not None
        assert prop.setter is not None

    def test_get_property_group_not_found(self) -> None:
        """Test getting property group that doesn't exist."""
        source = """
class Employee:
    pass
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        prop = handler.get_property_group("nonexistent", "Employee")

        assert prop is None

    def test_remove_property_from_class(self) -> None:
        """Test removing a property from a class."""
        source = """
class Employee:
    @property
    def sales_target(self):
        return self._sales_target

    @sales_target.setter
    def sales_target(self, value):
        self._sales_target = value

    def regular_method(self):
        pass
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        class_def = module.body[0]
        updated_class = handler.remove_property_from_class(class_def, "sales_target")

        # Should only have regular_method left
        methods = [stmt for stmt in updated_class.body.body if isinstance(stmt, cst.FunctionDef)]
        assert len(methods) == 1
        assert methods[0].name.value == "regular_method"

    def test_remove_property_from_class_leaves_pass_if_empty(self) -> None:
        """Test that removing the only property leaves a pass statement."""
        source = """
class Employee:
    @property
    def sales_target(self):
        return self._sales_target

    @sales_target.setter
    def sales_target(self, value):
        self._sales_target = value
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        class_def = module.body[0]
        updated_class = handler.remove_property_from_class(class_def, "sales_target")

        # Should have a pass statement
        assert len(updated_class.body.body) == 1
        stmt = updated_class.body.body[0]
        assert isinstance(stmt, cst.SimpleStatementLine)
        assert isinstance(stmt.body[0], cst.Pass)

    def test_add_property_to_class(self) -> None:
        """Test adding a property to a class."""
        source = """
class Salesman:
    def __init__(self):
        self._sales_target = 10000
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        # Create property definition to add
        prop_source = """
class Temp:
    @property
    def sales_target(self):
        return self._sales_target

    @sales_target.setter
    def sales_target(self, value):
        self._sales_target = value
"""
        prop_module = cst.parse_module(prop_source)
        prop_class = prop_module.body[0]
        getter = prop_class.body.body[0]
        setter = prop_class.body.body[1]

        prop_def = PropertyDefinition(
            name="sales_target",
            getter=getter,
            setter=setter,
            deleter=None
        )

        class_def = module.body[0]
        updated_class = handler.add_property_to_class(class_def, prop_def)

        # Should have __init__, getter, and setter
        methods = [stmt for stmt in updated_class.body.body if isinstance(stmt, cst.FunctionDef)]
        assert len(methods) == 3
        method_names = {m.name.value for m in methods}
        assert method_names == {"__init__", "sales_target"}

    def test_add_property_to_empty_class(self) -> None:
        """Test adding a property to an empty class with only pass."""
        source = """
class Salesman:
    pass
"""
        module = cst.parse_module(source)
        handler = PropertyMethodHandler(module)

        # Create property definition to add
        prop_source = """
class Temp:
    @property
    def sales_target(self):
        return self._sales_target
"""
        prop_module = cst.parse_module(prop_source)
        prop_class = prop_module.body[0]
        getter = prop_class.body.body[0]

        prop_def = PropertyDefinition(
            name="sales_target",
            getter=getter,
            setter=None,
            deleter=None
        )

        class_def = module.body[0]
        updated_class = handler.add_property_to_class(class_def, prop_def)

        # Should have getter and no pass statement
        methods = [stmt for stmt in updated_class.body.body if isinstance(stmt, cst.FunctionDef)]
        assert len(methods) == 1
        assert methods[0].name.value == "sales_target"

        # Should not have pass statement
        pass_stmts = [stmt for stmt in updated_class.body.body
                      if isinstance(stmt, cst.SimpleStatementLine)
                      and any(isinstance(b, cst.Pass) for b in stmt.body)]
        assert len(pass_stmts) == 0
