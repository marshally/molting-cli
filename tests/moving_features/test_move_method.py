"""
Tests for Move Method refactoring.

This module tests the Move Method refactoring which moves a method to the class that uses it most.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestMoveMethod(RefactoringTestBase):
    """Tests for Move Method refactoring."""

    fixture_category = "moving_features/move_method"

    def test_simple(self) -> None:
        """Move a method to the class that uses it most."""
        self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")

    def test_with_locals(self) -> None:
        """Test move method with local variables."""
        self.refactor("move-method", source="Account::calculate_fees", to="AccountType")

    def test_with_instance_vars(self) -> None:
        """Test move method with instance variables."""
        self.refactor("move-method", source="Account::calculate_interest", to="AccountType")

    def test_with_decorators(self) -> None:
        """Test move method with decorated methods."""
        self.refactor("move-method", source="Account::balance", to="AccountType")

    def test_multiple_calls(self) -> None:
        """Test move method with multiple call sites."""
        self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")

    def test_name_conflict(self) -> None:
        """Test move method when target class already has method with same name."""
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")
