"""Tests for Preserve Whole Object refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestPreserveWholeObject(RefactoringTestBase):
    """Tests for Preserve Whole Object refactoring."""

    fixture_category = "simplifying_method_calls/preserve_whole_object"

    def test_simple(self) -> None:
        """Send the whole object instead of extracting values from it."""
        self.refactor("preserve-whole-object", target="within_plan")

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test preserve whole object with multiple call sites."""
        self.refactor("preserve-whole-object", target="within_plan")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test preserve whole object with local variables."""
        self.refactor("preserve-whole-object", target="can_withdraw")
