"""
Tests for Move Method refactoring.

This module tests the Move Method refactoring which moves a method to the class that uses it most.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestMoveMethod(RefactoringTestBase):
    """Tests for Move Method refactoring."""

    fixture_category = "moving_features/move_method"

    def test_simple(self) -> None:
        """Test moving a simple method with no dependencies on source class state.

        This is the baseline case that verifies the core move method transformation
        works for methods with no instance variable access or local variable
        complexity. Essential for confirming basic functionality before testing
        more complex scenarios.
        """
        self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")

    def test_with_locals(self) -> None:
        """Test moving a method that uses local variables.

        Unlike test_simple, this method contains local variable declarations
        that must be preserved and properly scoped during the move. Tests the
        transformation handles variable scope and initialization correctly.
        """
        self.refactor("move-method", source="Account::calculate_fees", to="AccountType")

    def test_with_instance_vars(self) -> None:
        """Test moving a method that accesses instance variables from source class.

        This is the most important real-world scenario: moving methods that depend
        on source class state (self.field references). Verifies that instance variable
        accesses are correctly transformed to use parameters or delegation mechanisms.
        """
        self.refactor("move-method", source="Account::calculate_interest", to="AccountType")

    def test_with_decorators(self) -> None:
        """Test moving a method that has decorators (e.g., @property, @staticmethod).

        Unlike simpler methods, decorated methods have additional metadata that must
        be preserved and correctly adapted during the move. Ensures decorators are
        transferred and remain valid in the target class context.
        """
        self.refactor("move-method", source="Account::balance", to="AccountType")

    def test_multiple_calls(self) -> None:
        """Test moving a method that is called from multiple locations in the source code.

        When a method is called from multiple places, all call sites must be updated
        to use the new location (either the moved method or a delegating stub).
        Tests that the refactoring correctly updates all callers, not just one.
        """
        self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")

    def test_name_conflict(self) -> None:
        """Test that move method raises error when target class has a method with the same name.

        This is an error handling test that verifies the refactoring correctly
        detects naming conflicts and prevents the operation from proceeding.
        Important for maintaining code integrity and preventing silent overwrites.
        """
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")

    @pytest.mark.skip(reason="Multi-file refactoring not yet implemented")
    def test_multi_file(self) -> None:
        """Test move-method when call sites span multiple files.

        Moves Customer.calculate_discount to Order and updates all call sites
        in checkout.py from customer.calculate_discount(order) to
        order.calculate_discount(customer.discount_rate).
        """
        self.refactor_directory(
            "move-method", target="customer.py", source="Customer::calculate_discount", to="Order"
        )
