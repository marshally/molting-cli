"""Tests for Hide Method refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestHideMethod(RefactoringTestBase):
    """Tests for Hide Method refactoring."""

    fixture_category = "simplifying_method_calls/hide_method"

    def test_simple(self) -> None:
        """Make the method private."""
        self.refactor("hide-method", target="Employee::get_bonus_multiplier")

    def test_with_decorators(self) -> None:
        """Test hide method with decorated methods."""
        self.refactor("hide-method", target="Calculator::calculate_discount_rate")

    def test_with_instance_vars(self) -> None:
        """Test hide method with instance variables."""
        self.refactor("hide-method", target="PriceCalculator::apply_discount")
