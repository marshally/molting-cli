"""Tests for Inline Method refactoring.

This module tests the Inline Method refactoring which allows replacing
calls to a method with the method's body using rope's inline refactoring.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestInlineMethodSimple(RefactoringTestBase):
    """Tests for inlining simple methods."""
    fixture_category = "composing_methods/inline_method"

    def test_simple(self):
        """Inline a simple method."""
        self.refactor(
            "inline",
            target="Person::more_than_five_late_deliveries"
        )
