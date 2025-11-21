"""
Tests for Move Method refactoring implementation using TDD.
"""

from tests.conftest import RefactoringTestBase


class TestMoveMethodBasic(RefactoringTestBase):
    """Tests for Move Method refactoring - basic functionality."""

    fixture_category = "moving_features/move_method"

    def test_simple(self):
        """Test moving a method from one class to another."""
        self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")
