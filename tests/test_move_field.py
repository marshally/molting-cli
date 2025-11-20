"""Tests for Move Field refactoring.

This module tests the Move Field refactoring which allows moving
a field from one class to another using rope's move refactoring.
"""
import pytest
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestMoveField(RefactoringTestBase):
    """Tests for Move Field refactoring."""
    fixture_category = "moving_features/move_field"

    def test_simple(self):
        """Move a field from one class to another."""
        self.refactor(
            "move-field",
            source="Account::interest_rate",
            to="AccountType"
        )
