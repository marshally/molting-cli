"""
Tests for Decompose Conditional refactoring.

This refactoring extracts the condition and each branch into separate methods.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestDecomposeConditional(RefactoringTestBase):
    """Tests for Decompose Conditional refactoring."""

    fixture_category = "simplifying_conditionals/decompose_conditional"

    def test_simple(self) -> None:
        """Extract the condition and each branch into separate methods."""
        self.refactor("decompose-conditional", target="calculate_charge#L2-L5")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test decompose conditional with local variables."""
        self.refactor("decompose-conditional", target="process_order#L8-L13")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test decompose conditional with instance variables."""
        self.refactor("decompose-conditional", target="PricingCalculator::calculate_charge#L11-L14")

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test decompose conditional with multiple call sites."""
        self.refactor("decompose-conditional", target="calculate_shipping_charge#L5-L8")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test decompose conditional with decorated methods."""
        self.refactor("decompose-conditional", target="PriceCalculator::charge#L14-L17")
