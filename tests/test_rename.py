"""Tests for Rename refactoring.

This module tests the Rename refactoring which allows renaming
variables, methods, classes, or modules using rope's rename capability.
"""
from tests.conftest import RefactoringTestBase


class TestRenameFunction(RefactoringTestBase):
    """Tests for renaming functions."""
    fixture_category = "composing_methods/rename"

    def test_simple(self):
        """Rename a simple function."""
        self.refactor(
            "rename",
            target="add_numbers",
            new_name="calculate_sum"
        )
