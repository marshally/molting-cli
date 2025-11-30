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
