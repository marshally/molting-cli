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
        """Test basic decompose conditional on a simple if-else statement.

        This is the simplest case: extracting a simple conditional with two branches
        into separate methods. Verifies the core transformation works before testing
        more complex scenarios with local variables, instance variables, or multiple calls.
        """
        self.refactor("decompose-conditional", target="calculate_charge#L2-L5")

    def test_with_locals(self) -> None:
        """Test decompose conditional when branches use local variables.

        Unlike test_simple, this tests extraction when the conditional branches
        reference local variables. Verifies that local variables are correctly
        passed as parameters to the extracted methods while preserving semantics.
        """
        self.refactor("decompose-conditional", target="process_order#L9-L14")

    def test_with_instance_vars(self) -> None:
        """Test decompose conditional when branches use instance variables.

        This tests extraction in an instance method where the conditional branches
        reference instance (self) variables. Unlike test_with_locals, instance variables
        do not need to be passed as parameters; they remain accessible via self.
        """
        self.refactor("decompose-conditional", target="PricingCalculator::calculate_charge#L11-L14")

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test decompose conditional when the extracted condition is called multiple times.

        This tests a scenario where the extracted condition/methods are used in multiple
        call sites. Ensures the refactoring doesn't break other code that depends on
        the extracted logic being refactored.
        """
        self.refactor("decompose-conditional", target="calculate_shipping_charge#L5-L8")

    def test_with_decorators(self) -> None:
        """Test decompose conditional on a method with decorators.

        This tests extraction when the containing method has decorators (e.g., @property,
        @lru_cache, @staticmethod, etc.). Verifies that decorators are preserved and
        don't interfere with the extraction logic.
        """
        self.refactor("decompose-conditional", target="PriceCalculator::charge#L14-L17")
