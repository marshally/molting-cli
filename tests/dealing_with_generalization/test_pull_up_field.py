"""
Tests for Pull Up Field refactoring.

This refactoring moves a field from subclasses to their superclass,
consolidating common attributes in the class hierarchy.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestPullUpField(RefactoringTestBase):
    """Tests for Pull Up Field refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_field"

    def test_simple(self) -> None:
        """Move a field from subclasses to the superclass."""
        self.refactor("pull-up-field", target="Salesman::name", to="Employee")

    def test_with_instance_vars(self) -> None:
        """Test pull-up-field with instance variables."""
        self.refactor("pull-up-field", target="Salesman::name", to="Employee")

    def test_name_conflict(self) -> None:
        """Test pull-up-field when target field already exists in parent."""
        self.refactor("pull-up-field", target="Salesman::name", to="Employee")

    def test_with_decorators(self) -> None:
        """Test pull-up-field with decorated property methods."""
        self.refactor("pull-up-field", target="Salesman::commission_rate", to="Employee")

    def test_multiple_calls(self) -> None:
        """Test pull-up-field with multiple call sites."""
        self.refactor("pull-up-field", target="Salesman::name", to="Employee")
