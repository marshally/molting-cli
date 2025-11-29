"""Tests for Substitute Algorithm refactoring.

Tests for the Substitute Algorithm refactoring, which replaces
an algorithm with a clearer one.
"""

from tests.conftest import RefactoringTestBase


class TestSubstituteAlgorithm(RefactoringTestBase):
    """Tests for Substitute Algorithm refactoring."""

    fixture_category = "composing_methods/substitute_algorithm"

    def test_simple(self) -> None:
        """Test basic substitute algorithm refactoring.

        This tests the core algorithm substitution: replacing an existing
        algorithm (e.g., a loop-based search) with a clearer or more efficient
        alternative (e.g., using built-in methods). This is a foundational test
        ensuring the transformation mechanics work correctly.
        """
        self.refactor("substitute-algorithm", target="found_person")
