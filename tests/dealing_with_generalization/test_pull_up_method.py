"""
Tests for Pull Up Method refactoring.

This refactoring moves a method from subclasses to their superclass,
consolidating common behavior in the class hierarchy.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestPullUpMethod(RefactoringTestBase):
    """Tests for Pull Up Method refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_method"

    def test_simple(self) -> None:
        """Move identical methods from subclasses to the superclass."""
        self.refactor("pull-up-method", target="Salesman::get_annual_cost", to="Employee")

    def test_with_instance_vars(self) -> None:
        """Test pull-up-method with instance variables."""
        self.refactor("pull-up-method", target="Salesman::get_employee_info", to="Employee")

    def test_name_conflict(self) -> None:
        """Test pull-up-method when target method already exists in parent."""
        self.refactor("pull-up-method", target="Salesman::get_annual_cost", to="Employee")

    def test_with_decorators(self) -> None:
        """Test pull-up-method with @staticmethod decorator."""
        self.refactor("pull-up-method", target="Salesman::format_currency", to="Employee")

    def test_multiple_calls(self) -> None:
        """Test pull-up-method with multiple call sites."""
        self.refactor("pull-up-method", target="Salesman::get_annual_cost", to="Employee")
