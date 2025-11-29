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
        """Extract expression into a method and replace temp."""
        self.refactor("replace-temp-with-query", target="Order::get_price::base_price")

    def test_with_locals(self) -> None:
        """Test replace temp with query with local variables used multiple times."""
        self.refactor("replace-temp-with-query", target="Invoice::calculate_total::base_price")

    def test_with_instance_vars(self) -> None:
        """Test replace temp with query with instance variables."""
        # Replace discounted_price temp with a query method that uses instance vars
        self.refactor(
            "replace-temp-with-query", target="Product::get_final_price::discounted_price"
        )

    def test_name_conflict(self) -> None:
        """Test replace temp with query when method name already exists."""
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard
        # Try to replace base_price temp with a method but the method already exists
        with pytest.raises(ValueError, match="already exists"):
            refactor_file(
                "replace-temp-with-query", self.test_file, target="Order::get_price::base_price"
            )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test replace temp with query with decorated methods."""
        # Replace perimeter temp in @property decorated area method
        self.refactor("replace-temp-with-query", target="Rectangle::area::perimeter")
