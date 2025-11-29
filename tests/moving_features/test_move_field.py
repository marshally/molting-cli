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
        """Test moving a simple field with no complex dependencies.

        This baseline case verifies the core move field transformation works
        for straightforward field relocations. Tests basic field declaration,
        initialization, and access migration before adding complexity.
        """
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    def test_multiple_calls(self) -> None:
        """Test moving a field that is accessed from multiple locations in source code.

        Unlike test_simple which may have limited field accesses, this test verifies
        that all field read and write operations across the codebase are correctly
        updated to access the field in its new location.
        """
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    def test_with_instance_vars(self) -> None:
        """Test moving a field that interacts with other instance variables.

        This tests field moves in contexts where the field has relationships with
        other instance variables (e.g., initialization dependencies, update patterns).
        Verifies that the refactoring preserves semantic correctness across related fields.
        """
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    def test_name_conflict(self) -> None:
        """Test that move field raises error when target class has a field with the same name.

        This error handling test verifies the refactoring detects field name collisions
        and prevents the move operation. Critical for preventing silent field overwrites
        that would cause data loss or logic errors.
        """
        with pytest.raises(ValueError, match="already has a field"):
            self.refactor("move-field", source="Account::interest_rate", to="AccountType")
