"""Tests for Remove Assignments to Parameters refactoring.

Tests for the Remove Assignments to Parameters refactoring, which uses
a temp variable instead of assigning to parameters.
"""

from tests.conftest import RefactoringTestBase


class TestRemoveAssignmentsToParameters(RefactoringTestBase):
    """Tests for Remove Assignments to Parameters refactoring."""

    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_simple(self) -> None:
        """Use a temp variable instead of assigning to parameters."""
        self.refactor("remove-assignments-to-parameters", target="discount")
