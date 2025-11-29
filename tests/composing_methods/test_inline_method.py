"""Tests for Inline Method refactoring.

Tests for the Inline Method refactoring, which inlines a method
whose body is as clear as its name.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestInlineMethod(RefactoringTestBase):
    """Tests for Inline Method refactoring."""

    fixture_category = "composing_methods/inline_method"

    def test_simple(self) -> None:
        """Inline a simple method whose body is as clear as its name."""
        self.refactor("inline-method", target="Person::more_than_five_late_deliveries")

    def test_with_instance_vars(self) -> None:
        """Test inline method with instance variables."""
        # Inline get_subtotal which uses self.items
        self.refactor("inline-method", target="ShoppingCart::get_subtotal")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test inline method with decorated methods."""
        # Inline _get_base_total into the @property decorated total method
        self.refactor("inline-method", target="ShoppingCart::_get_base_total")

    def test_multiple_calls(self) -> None:
        """Test inline method with multiple call sites."""
        self.refactor("inline-method", target="Person::more_than_five_late_deliveries")
