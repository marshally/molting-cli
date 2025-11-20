"""Tests for Remove Assignments to Parameters refactoring.

This module tests the Remove Assignments to Parameters refactoring which
replaces parameter reassignments with local variables using libcst.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestRemoveAssignmentsToParametersSimple(RefactoringTestBase):
    """Tests for removing simple parameter assignments."""
    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_simple(self):
        """Remove assignments to a single parameter."""
        self.refactor(
            "remove-assignments-to-parameters",
            target="discount"
        )
