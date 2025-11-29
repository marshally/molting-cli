"""
Tests for Replace Array with Object refactoring.

This test module verifies the replace-array-with-object refactoring,
which replaces an array with an object that has named fields.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceArrayWithObject(RefactoringTestBase):
    """Tests for Replace Array with Object refactoring."""

    fixture_category = "organizing_data/replace_array_with_object"

    def test_simple(self) -> None:
        """Replace an array with an object that has a field for each element."""
        self.refactor(
            "replace-array-with-object", target="analyze_performance::row", name="Performance"
        )

    @pytest.mark.skip(
        reason=(
            "Implementation needed for with_locals - only transforms first function, "
            "not all functions with same parameter"
        )
    )
    def test_with_locals(self) -> None:
        """Test replace array with object with local variables."""
        self.refactor(
            "replace-array-with-object", target="analyze_performance::row", name="Performance"
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace array with object when target name already exists."""
        with pytest.raises(ValueError, match="Class.*Performance.*already exists"):
            self.refactor(
                "replace-array-with-object", target="analyze_performance::row", name="Performance"
            )
