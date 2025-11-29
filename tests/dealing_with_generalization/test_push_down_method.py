"""
Tests for Push Down Method refactoring.

This refactoring moves a method from a superclass to those subclasses
that specifically need it.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestPushDownMethod(RefactoringTestBase):
    """Tests for Push Down Method refactoring."""

    fixture_category = "dealing_with_generalization/push_down_method"

    def test_simple(self) -> None:
        """Move a method from superclass to those subclasses that need it."""
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")

    def test_with_instance_vars(self) -> None:
        """Test push-down-method with instance variables."""
        self.refactor("push-down-method", target="Employee::calculate_bonus", to="Salesman")

    def test_name_conflict(self) -> None:
        """Test push-down-method when target subclass already has method."""
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")

    def test_with_decorators(self) -> None:
        """Test push-down-method with @classmethod decorator."""
        self.refactor("push-down-method", target="Employee::create_from_config", to="Salesman")

    def test_multiple_calls(self) -> None:
        """Test push-down-method with multiple call sites."""
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")
