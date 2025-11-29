"""
Tests for Duplicate Observed Data refactoring.

This test module verifies the duplicate-observed-data refactoring,
which copies data from domain objects to GUI objects using the observer pattern.
"""

from tests.conftest import RefactoringTestBase


class TestDuplicateObservedData(RefactoringTestBase):
    """Tests for Duplicate Observed Data refactoring."""

    fixture_category = "organizing_data/duplicate_observed_data"

    def test_simple(self) -> None:
        """Test basic duplicate-observed-data to synchronize GUI and domain objects.

        This is the simplest case: copying a data field from a domain object to a GUI
        object and establishing bidirectional observer synchronization. Verifies the
        core transformation that keeps UI and domain data in sync.
        """
        self.refactor(
            "duplicate-observed-data",
            target="IntervalWindow::start_field",
            domain="Interval",
            field_suffix="_field",
            focus_handler="start_field_focus_lost",
        )
