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
        """Test basic split temporary variable refactoring.

        This is the simplest case: a method with a single temporary variable that
        is assigned multiple times for different purposes. The refactoring should
        split this into separate variables with more meaningful names, improving
        code clarity and reducing cognitive load.
        """
        self.refactor("split-temporary-variable", target="calculate_distance::temp")

    def test_name_conflict(self) -> None:
        """Test that name conflict is detected when the new variable name already exists.

        This test verifies error handling: when splitting a temporary variable,
        if the proposed name for the split variable (e.g., primary_acc) already
        exists in the scope, the refactoring should raise a ValueError instead of
        silently overwriting or creating shadowing variables.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard
        # Try to split temp to primary_acc but it already exists - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            refactor_file(
                "split-temporary-variable", self.test_file, target="calculate_distance::temp"
            )
