"""
Tests for Replace Conditional with Polymorphism refactoring.

This refactoring moves each conditional leg to an overriding method in a subclass.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceConditionalWithPolymorphism(RefactoringTestBase):
    """Tests for Replace Conditional with Polymorphism refactoring."""

    fixture_category = "simplifying_conditionals/replace_conditional_with_polymorphism"

    def test_simple(self) -> None:
        """Move each conditional leg to an overriding method in a subclass."""
        self.refactor(
            "replace-conditional-with-polymorphism", target="Employee::pay_amount#L13-L20"
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test replace conditional with polymorphism with heavy instance variable usage."""
        self.refactor(
            "replace-conditional-with-polymorphism",
            target="ShippingCalculator::calculate_cost#L16-L27",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test replace conditional with polymorphism with decorated methods."""
        self.refactor(
            "replace-conditional-with-polymorphism", target="Employee::pay_amount#L17-L24"
        )
