"""Tests for Substitute Algorithm refactoring.

Tests for the Substitute Algorithm refactoring, which replaces
an algorithm with a clearer one.
"""

from tests.conftest import RefactoringTestBase


class TestSubstituteAlgorithm(RefactoringTestBase):
    """Tests for Substitute Algorithm refactoring."""

    fixture_category = "composing_methods/substitute_algorithm"

    def test_simple(self) -> None:
        """Replace an algorithm with a clearer one."""
        self.refactor("substitute-algorithm", target="found_person")
