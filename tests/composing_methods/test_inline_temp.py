"""Tests for Inline Temp refactoring.

Tests for the Inline Temp refactoring, which replaces a temp variable
with its expression.
"""

from tests.conftest import RefactoringTestBase


class TestInlineTemp(RefactoringTestBase):
    """Tests for Inline Temp refactoring."""

    fixture_category = "composing_methods/inline_temp"

    def test_simple(self) -> None:
        """Test basic inline temp refactoring.

        This is the simplest case: a temporary variable that is assigned a value
        once and then used once. The refactoring should replace the variable usage
        with the assigned expression, eliminating the intermediate variable and
        simplifying the code.
        """
        self.refactor("inline-temp", target="calculate_total::base_price")

    def test_with_locals(self) -> None:
        """Test inline temp when the variable is used in multiple places.

        Unlike test_simple where a variable is used once, this case tests when
        a temporary variable is referenced multiple times. The refactoring must
        correctly replace all occurrences with the assigned expression, or
        handle the case where inlining is not beneficial.
        """
        self.refactor("inline-temp", target="calculate_price::base_price")
