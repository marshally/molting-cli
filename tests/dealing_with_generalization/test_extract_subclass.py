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
        """Test basic extraction of a subclass for specialized features.

        Creates a new LaborItem subclass from JobItem and moves the is_labor field
        and employee field to it. This is the simplest case: extracting a few
        related features into a new subclass. Verifies the core subclass creation
        and feature extraction works before testing edge cases.
        """
        self.refactor(
            "extract-subclass", target="JobItem", features="is_labor,employee", name="LaborItem"
        )

    def test_name_conflict(self) -> None:
        """Test extract-subclass when the proposed subclass name already exists.

        Unlike test_simple, this verifies proper handling when the proposed subclass
        name (LaborItem) conflicts with an existing class in the codebase. The
        refactoring should either raise an appropriate error or handle the conflict
        gracefully.
        """
        self.refactor(
            "extract-subclass", target="JobItem", features="is_labor,employee", name="LaborItem"
        )
