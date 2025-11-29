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
        """Create a superclass and move common features to it."""
        self.refactor("extract-superclass", targets="Employee,Department", name="Party")

    def test_name_conflict(self) -> None:
        """Test extract-superclass when target superclass name already exists."""
        self.refactor("extract-superclass", targets="Employee,Department", name="Party")
