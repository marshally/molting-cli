"""Tests for Replace Temp with Query refactoring.

Tests for the Replace Temp with Query refactoring, which extracts
an expression into a method and replaces the temp variable with
calls to that method.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceTempWithQuery(RefactoringTestBase):
    """Tests for Replace Temp with Query refactoring."""

    fixture_category = "composing_methods/replace_temp_with_query"

    def test_simple(self) -> None:
        """Test basic replace temp with query refactoring.

        This is the simplest case: a temporary variable holding a computed
        expression is replaced with calls to a new query method. This eliminates
        the temporary variable and makes the computation reusable. The test verifies
        that the method extraction and all temp references are correctly updated.
        """
        self.refactor("replace-temp-with-query", target="Order::get_price::base_price")

    def test_with_locals(self) -> None:
        """Test replace temp with query when temp variable is used multiple times.

        Unlike test_simple where the temp may be used once, this case tests when
        a temporary variable is referenced in multiple places within the method.
        The refactoring must correctly replace all occurrences with method calls,
        ensuring the extracted method is invoked each time the value is needed.
        """
        self.refactor("replace-temp-with-query", target="Invoice::calculate_total::base_price")

    def test_with_instance_vars(self) -> None:
        """Test replace temp with query when the extracted method uses instance variables.

        This case tests a more complex scenario where the temporary variable's
        expression depends on instance variables (e.g., self.price, self.discount).
        The extracted query method must be an instance method that can access these
        instance variables, not a static or standalone function.
        """
        # Replace discounted_price temp with a query method that uses instance vars
        self.refactor(
            "replace-temp-with-query", target="Product::get_final_price::discounted_price"
        )

    def test_name_conflict(self) -> None:
        """Test that name conflict is detected when the query method name already exists.

        This test verifies error handling: when replacing a temp with a query,
        the refactoring must extract the expression into a new method. If a method
        with the proposed name (e.g., base_price) already exists, it should raise
        a ValueError to prevent overwriting existing functionality.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard
        # Try to replace base_price temp with a method but the method already exists
        with pytest.raises(ValueError, match="already exists"):
            refactor_file(
                "replace-temp-with-query", self.test_file, target="Order::get_price::base_price"
            )

    def test_with_decorators(self) -> None:
        """Test replace temp with query when the containing method has decorators.

        This case (currently skipped) tests extracting a temporary variable into
        a query method when the original method is decorated (e.g., @property).
        The refactoring must handle decorator preservation and ensure the extracted
        query method works correctly within the decorated context.
        """
        # Replace perimeter temp in @property decorated area method
        self.refactor("replace-temp-with-query", target="Rectangle::area::perimeter")
