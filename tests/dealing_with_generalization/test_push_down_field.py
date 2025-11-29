"""
Tests for Push Down Field refactoring.

This refactoring moves a field from a superclass to those subclasses
that specifically need it.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestPushDownField(RefactoringTestBase):
    """Tests for Push Down Field refactoring."""

    fixture_category = "dealing_with_generalization/push_down_field"

    def test_simple(self) -> None:
        """Move a field from superclass to those subclasses that need it."""
        self.refactor("push-down-field", target="Employee::quota", to="Salesman")

    def test_with_instance_vars(self) -> None:
        """Test push-down-field with instance variables."""
        self.refactor("push-down-field", target="Employee::commission_rate", to="Salesman")

    def test_name_conflict(self) -> None:
        """Test push-down-field when target subclass already has field."""
        self.refactor("push-down-field", target="Employee::quota", to="Salesman")

    @pytest.mark.skip(reason="Implementation needed for decorated properties")
    def test_with_decorators(self) -> None:
        """Test push-down-field with decorated property methods."""
        self.refactor("push-down-field", target="Employee::sales_target", to="Salesman")

    def test_multiple_calls(self) -> None:
        """Test push-down-field with multiple call sites."""
        self.refactor("push-down-field", target="Employee::quota", to="Salesman")
