"""Tests for Inline Temp refactoring.

Tests for the Inline Temp refactoring, which replaces a temp variable
with its expression.
"""

from tests.conftest import RefactoringTestBase


class TestInlineTemp(RefactoringTestBase):
    """Tests for Inline Temp refactoring."""

    fixture_category = "composing_methods/inline_temp"

    def test_simple(self) -> None:
        """Replace a temp variable with its expression."""
        self.refactor("inline-temp", target="calculate_total::base_price")

    def test_with_locals(self) -> None:
        """Test inline temp with local variables used in multiple places."""
        self.refactor("inline-temp", target="calculate_price::base_price")
