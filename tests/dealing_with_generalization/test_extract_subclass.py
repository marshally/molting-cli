"""
Tests for Extract Subclass refactoring.

This refactoring creates a subclass for a subset of features, allowing
specialized behavior for certain instances of a class.
"""


from tests.conftest import RefactoringTestBase


class TestExtractSubclass(RefactoringTestBase):
    """Tests for Extract Subclass refactoring."""

    fixture_category = "dealing_with_generalization/extract_subclass"

    def test_simple(self) -> None:
        """Create a subclass for a subset of features."""
        self.refactor(
            "extract-subclass", target="JobItem", features="is_labor,employee", name="LaborItem"
        )

    def test_name_conflict(self) -> None:
        """Test extract-subclass when target subclass name already exists."""
        self.refactor(
            "extract-subclass", target="JobItem", features="is_labor,employee", name="LaborItem"
        )
