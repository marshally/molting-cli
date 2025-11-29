"""
Tests for Extract Superclass refactoring.

This refactoring creates a superclass and moves common features from
multiple classes into it.
"""

from tests.conftest import RefactoringTestBase


class TestExtractSuperclass(RefactoringTestBase):
    """Tests for Extract Superclass refactoring."""

    fixture_category = "dealing_with_generalization/extract_superclass"

    def test_simple(self) -> None:
        """Test basic extraction of a superclass from multiple classes.

        Creates a new Party superclass and moves common fields and methods from
        both Employee and Department into it. This is the simplest case: extracting
        common features from exactly two classes. Verifies the core superclass
        creation and feature extraction works before testing edge cases.
        """
        self.refactor("extract-superclass", targets="Employee,Department", name="Party")

    def test_name_conflict(self) -> None:
        """Test extract-superclass when the proposed superclass name already exists.

        Unlike test_simple, this verifies proper handling when the proposed superclass
        name (Party) conflicts with an existing class in the codebase. The refactoring
        should either raise an appropriate error or handle the conflict gracefully.
        """
        self.refactor("extract-superclass", targets="Employee,Department", name="Party")
