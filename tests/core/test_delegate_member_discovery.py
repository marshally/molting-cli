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
