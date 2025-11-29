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
        """Test basic replacement of an array parameter with an object.

        This is the simplest case: converting a primitive array into an object with
        named fields for each array element. Verifies the core transformation works
        before testing cases with local variables or name conflicts.
        """
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
        """Test array-to-object replacement when functions use local variables with the same name.

        Unlike test_simple which uses array parameters, this verifies that local variable
        arrays are properly transformed. Currently skipped as the implementation only transforms
        the first function occurrence, not all functions sharing the same parameter/variable name.
        """
        self.refactor(
            "replace-array-with-object", target="analyze_performance::row", name="Performance"
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test that replacing array fails when the target class name already exists.

        Unlike test_simple which creates a new class, this verifies proper error handling
        when the requested class name (Performance) would conflict with an existing class.
        This is important to prevent accidental overwriting of existing code.
        Currently skipped as implementation needs to detect and report class name conflicts.
        """
        with pytest.raises(ValueError, match="Class.*Performance.*already exists"):
            self.refactor(
                "replace-array-with-object", target="analyze_performance::row", name="Performance"
            )
