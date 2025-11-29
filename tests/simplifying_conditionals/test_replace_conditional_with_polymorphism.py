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
        """Test replacing a type-based conditional with polymorphism.

        This is the simplest case: a conditional checking an object's type and calling
        different logic for each type is replaced with subclass method overrides.
        Verifies the core polymorphic transformation works before testing with instance
        variables or decorated methods.
        """
        self.refactor(
            "replace-conditional-with-polymorphism", target="Employee::pay_amount#L13-L20"
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test polymorphic replacement with heavy use of instance variables.

        Unlike test_simple, this tests the transformation when the conditional branches
        heavily use instance variables (self.field). Verifies that instance variable
        access is correctly handled when moving logic to subclass overrides.
        """
        self.refactor(
            "replace-conditional-with-polymorphism",
            target="ShippingCalculator::calculate_cost#L16-L27",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test polymorphic replacement on a method with decorators.

        This tests the transformation when the containing method has decorators
        (e.g., @property, @cached, @staticmethod, etc.). Verifies that decorators
        are preserved when moving the method to subclass overrides.
        """
        self.refactor(
            "replace-conditional-with-polymorphism", target="Employee::pay_amount#L17-L24"
        )
