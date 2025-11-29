"""Tests for Split Temporary Variable refactoring.

Tests for the Split Temporary Variable refactoring, which splits
a variable that is assigned multiple times into separate variables.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestSplitTemporaryVariable(RefactoringTestBase):
    """Tests for Split Temporary Variable refactoring."""

    fixture_category = "composing_methods/split_temporary_variable"

    def test_simple(self) -> None:
        """Split a temp variable assigned multiple times."""
        self.refactor("split-temporary-variable", target="calculate_distance::temp")

    def test_name_conflict(self) -> None:
        """Test split temporary variable when new variable name already exists."""
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard
        # Try to split temp to primary_acc but it already exists - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            refactor_file(
                "split-temporary-variable", self.test_file, target="calculate_distance::temp"
            )
