"""
Tests for Move Field refactoring.

This module tests the Move Field refactoring which moves a field to the class that uses it most.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestMoveField(RefactoringTestBase):
    """Tests for Move Field refactoring."""

    fixture_category = "moving_features/move_field"

    def test_simple(self) -> None:
        """Move a field to the class that uses it most."""
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    def test_multiple_calls(self) -> None:
        """Test move field with multiple call sites."""
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    def test_with_instance_vars(self) -> None:
        """Test move field with instance variables."""
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    def test_name_conflict(self) -> None:
        """Test move field when target class already has field with same name."""
        with pytest.raises(ValueError, match="already has a field"):
            self.refactor("move-field", source="Account::interest_rate", to="AccountType")
