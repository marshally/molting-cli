"""Tests for Remove Assignments to Parameters refactoring.

Tests for the Remove Assignments to Parameters refactoring, which uses
a temp variable instead of assigning to parameters.
"""

from tests.conftest import RefactoringTestBase


class TestRemoveAssignmentsToParameters(RefactoringTestBase):
    """Tests for Remove Assignments to Parameters refactoring."""

    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_simple(self) -> None:
        """Test basic remove assignments to parameters refactoring.

        This is the simplest case: a method that assigns to a parameter and then
        uses it. The refactoring should introduce a local temp variable instead,
        making the parameter effectively final. This improves clarity by distinguishing
        between input parameters and locally modified values.
        """
        self.refactor("remove-assignments-to-parameters", target="discount")
