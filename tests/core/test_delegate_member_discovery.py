"""Tests for DelegateMemberDiscovery utility."""

import libcst as cst
import pytest

from molting.core.delegate_member_discovery import DelegateMemberDiscovery, DelegateMember


class TestFindDelegateClass:
    """Tests for finding the delegate class from __init__."""

    def test_find_delegate_class_from_parameter_type_hint(self):
        """Should find delegate class from type-hinted parameter."""
        source = """
class Employee:
    def __init__(self, compensation: Compensation):
        self.compensation = compensation

class Compensation:
    pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        result = discovery.find_delegate_class("Employee", "compensation")

        assert result == "Compensation"

    def test_find_delegate_class_from_assignment_without_type_hint(self):
        """Should return None when no type hint available (requires manual specification)."""
        source = """
class Employee:
    def __init__(self, compensation):
        self.compensation = compensation

class Compensation:
    pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        result = discovery.find_delegate_class("Employee", "compensation")

        # Without type hint, we can't auto-discover the class
        assert result is None

    def test_find_delegate_class_returns_none_for_nonexistent_field(self):
        """Should return None if field doesn't exist in __init__."""
        source = """
class Employee:
    def __init__(self, name: str):
        self.name = name
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        result = discovery.find_delegate_class("Employee", "compensation")

        assert result is None

    def test_find_delegate_class_returns_none_for_nonexistent_class(self):
        """Should return None if class doesn't exist."""
        source = """
class Person:
    def __init__(self):
        pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        result = discovery.find_delegate_class("Employee", "compensation")

        assert result is None


class TestEnumeratePublicMembers:
    """Tests for enumerating public members of a class."""

    def test_enumerate_fields_from_init(self):
        """Should find all fields assigned in __init__."""
        source = """
class Compensation:
    def __init__(self):
        self.salary = 0
        self.bonus_percentage = 0
        self.deduction_rate = 0
        self.tax_rate = 0
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        field_members = [m for m in members if m.kind == "field"]
        field_names = [m.name for m in field_members]
        assert set(field_names) == {"salary", "bonus_percentage", "deduction_rate", "tax_rate"}

    def test_enumerate_fields_excludes_private_fields(self):
        """Should exclude fields starting with underscore."""
        source = """
class Compensation:
    def __init__(self):
        self.salary = 0
        self._internal_cache = {}
        self.__private = 0
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        field_members = [m for m in members if m.kind == "field"]
        field_names = [m.name for m in field_members]
        assert field_names == ["salary"]

    def test_enumerate_empty_class(self):
        """Should return empty list for class with no public members."""
        source = """
class Compensation:
    pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        assert members == []

    def test_enumerate_nonexistent_class(self):
        """Should return empty list for nonexistent class."""
        source = """
class Employee:
    pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        assert members == []

    def test_enumerate_regular_methods(self):
        """Should find all public regular methods."""
        source = """
class Compensation:
    def calculate_gross_pay(self):
        pass

    def calculate_net_pay(self):
        pass

    def get_annual_compensation(self):
        pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        method_members = [m for m in members if m.kind == "method"]
        method_names = [m.name for m in method_members]
        assert set(method_names) == {"calculate_gross_pay", "calculate_net_pay", "get_annual_compensation"}

    def test_enumerate_methods_excludes_dunder_methods(self):
        """Should exclude __init__ and other dunder methods."""
        source = """
class Compensation:
    def __init__(self):
        pass

    def __str__(self):
        return "Compensation"

    def calculate_pay(self):
        pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        method_members = [m for m in members if m.kind == "method"]
        method_names = [m.name for m in method_members]
        assert method_names == ["calculate_pay"]

    def test_enumerate_methods_excludes_private_methods(self):
        """Should exclude methods starting with underscore."""
        source = """
class Compensation:
    def calculate_pay(self):
        pass

    def _internal_helper(self):
        pass

    def __private_method(self):
        pass
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        method_members = [m for m in members if m.kind == "method"]
        method_names = [m.name for m in method_members]
        assert method_names == ["calculate_pay"]

    def test_enumerate_property_methods(self):
        """Should find @property decorated methods."""
        source = """
class Compensation:
    @property
    def annual_bonus(self):
        return 1000

    @property
    def total_compensation(self):
        return 5000
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        property_members = [m for m in members if m.kind == "property"]
        property_names = [m.name for m in property_members]
        assert set(property_names) == {"annual_bonus", "total_compensation"}

    def test_enumerate_property_with_setter(self):
        """Should detect setter on property."""
        source = """
class Compensation:
    @property
    def salary(self):
        return self._salary

    @salary.setter
    def salary(self, value):
        self._salary = value
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        property_members = [m for m in members if m.kind == "property"]
        assert len(property_members) == 1
        assert property_members[0].name == "salary"
        assert property_members[0].has_setter is True
        assert property_members[0].has_deleter is False

    def test_enumerate_property_with_deleter(self):
        """Should detect deleter on property."""
        source = """
class Compensation:
    @property
    def salary(self):
        return self._salary

    @salary.deleter
    def salary(self):
        del self._salary
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        property_members = [m for m in members if m.kind == "property"]
        assert len(property_members) == 1
        assert property_members[0].name == "salary"
        assert property_members[0].has_setter is False
        assert property_members[0].has_deleter is True

    def test_enumerate_combined_fields_methods_properties(self):
        """Should enumerate all member types together."""
        source = """
class Compensation:
    def __init__(self):
        self.base_salary = 0
        self.bonus_rate = 0.1

    def calculate_gross_pay(self):
        pass

    @property
    def annual_bonus(self):
        return self.base_salary * self.bonus_rate
"""
        module = cst.parse_module(source)
        discovery = DelegateMemberDiscovery(module)

        members = discovery.enumerate_public_members("Compensation")

        field_names = [m.name for m in members if m.kind == "field"]
        method_names = [m.name for m in members if m.kind == "method"]
        property_names = [m.name for m in members if m.kind == "property"]

        assert set(field_names) == {"base_salary", "bonus_rate"}
        assert method_names == ["calculate_gross_pay"]
        assert property_names == ["annual_bonus"]
