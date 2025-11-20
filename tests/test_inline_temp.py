"""Tests for Inline Temp refactoring.

This module tests the Inline Temp refactoring which allows inlining
temporary variables using rope's inline refactoring capability.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestInlineTempSimple(RefactoringTestBase):
    """Tests for inlining simple temporary variables."""
    fixture_category = "composing_methods/inline_temp"

    def test_simple(self):
        """Inline a simple temporary variable."""
        self.refactor(
            "inline-temp",
            target="temp_value"
        )


class TestInlineTempMultipleUses(RefactoringTestBase):
    """Tests for inlining variables with multiple uses."""
    fixture_category = "composing_methods/inline_temp"

    def test_multiple_uses(self):
        """Inline a temporary variable with multiple uses."""
        self.refactor(
            "inline-temp",
            target="base_price"
        )
