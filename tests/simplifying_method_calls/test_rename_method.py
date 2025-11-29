"""Tests for Rename Method refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestRenameMethod(RefactoringTestBase):
    """Tests for Rename Method refactoring."""

    fixture_category = "simplifying_method_calls/rename_method"

    def test_simple(self) -> None:
        """Rename a method to better reveal its purpose."""
        self.refactor(
            "rename-method", target="Customer::get_inv_cdtlmt", new_name="get_invoice_credit_limit"
        )

    def test_with_instance_vars(self) -> None:
        """Test rename method with instance variables."""
        self.refactor(
            "rename-method", target="ShoppingCart::calc_amt", new_name="calculate_total_amount"
        )

    def test_with_decorators(self) -> None:
        """Test rename method with decorated methods."""
        self.refactor("rename-method", target="Product::n", new_name="name")

    def test_multiple_calls(self) -> None:
        """Test rename method with multiple call sites."""
        self.refactor(
            "rename-method", target="Customer::get_inv_cdtlmt", new_name="get_invoice_credit_limit"
        )

    def test_name_conflict(self) -> None:
        """Test rename method when target name already exists."""
        self.refactor(
            "rename-method", target="Customer::get_inv_cdtlmt", new_name="get_invoice_credit_limit"
        )
