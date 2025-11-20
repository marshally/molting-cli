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

    def test_nonexistent_source_field(self):
        """Test error when source field doesn't exist."""
        import pytest

        # Use simple fixture
        self.test_file = self.tmp_path / "input.py"
        self.test_file.write_text("""
class Account:
    def __init__(self):
        self.balance = 100.0

    def get_balance(self):
        return self.balance


class AccountType:
    pass
""")

        with pytest.raises(ValueError, match="Field 'nonexistent' not found"):
            from molting.refactorings.moving_features.move_field import MoveField
            refactor = MoveField(str(self.test_file), "Account::nonexistent", "AccountType")
            refactor.apply(self.test_file.read_text())

    def test_nonexistent_destination_class(self):
        """Test error when destination class doesn't exist."""
        import pytest

        # Use simple fixture
        self.test_file = self.tmp_path / "input.py"
        self.test_file.write_text("""
class Account:
    def __init__(self):
        self.interest_rate = 0.05

    def get_rate(self):
        return self.interest_rate
""")

        with pytest.raises(ValueError, match="Destination class 'NonExistent' not found"):
            from molting.refactorings.moving_features.move_field import MoveField
            refactor = MoveField(str(self.test_file), "Account::interest_rate", "NonExistent")
            refactor.apply(self.test_file.read_text())
