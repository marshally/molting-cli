"""
Tests for Duplicate Observed Data refactoring.

This test module verifies the duplicate-observed-data refactoring,
which copies data from domain objects to GUI objects using the observer pattern.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestDuplicateObservedData(RefactoringTestBase):
    """Tests for Duplicate Observed Data refactoring."""

    fixture_category = "organizing_data/duplicate_observed_data"

    def test_simple(self) -> None:
        """Copy data from domain object to GUI object and set up observer pattern."""
        self.refactor(
            "duplicate-observed-data", target="IntervalWindow::start_field", domain="Interval"
        )
