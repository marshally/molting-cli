"""Tests for Rename Method refactoring."""

from tests.conftest import RefactoringTestBase


class TestRenameMethod(RefactoringTestBase):
    """Tests for Rename Method refactoring."""

    fixture_category = "simplifying_method_calls/rename_method"

    def test_simple(self) -> None:
        """Test basic rename method with a single call site.

        This is the simplest case: renaming a method with an abbreviated
        name (get_inv_cdtlmt) to a more descriptive one (get_invoice_credit_limit).
        Verifies the core transformation works before testing multiple call sites
        or methods with decorators.
        """
        self.refactor(
            "rename-method", target="Customer::get_inv_cdtlmt", new_name="get_invoice_credit_limit"
        )

    def test_with_instance_vars(self) -> None:
        """Test rename method when the method uses instance variables.

        Unlike test_simple which renames a method from a simple class,
        this tests renaming a method that accesses instance variables
        (like self.items in ShoppingCart). Verifies that instance state
        references are preserved through the rename.
        """
        self.refactor(
            "rename-method", target="ShoppingCart::calc_amt", new_name="calculate_total_amount"
        )

    def test_with_decorators(self) -> None:
        """Test rename method when the method has decorators.

        This tests renaming a decorated method (e.g., with @property).
        The transformation must preserve all decorators while updating
        the method name. Different from test_simple which has no decorators.
        """
        self.refactor("rename-method", target="Product::n", new_name="name")

    def test_multiple_calls(self) -> None:
        """Test rename method when the method is called from multiple locations.

        Unlike test_simple which may only have one call site, this verifies
        that ALL call sites are updated when renaming a method. Missing even
        one call site would break the code, so this is critical for correctness.
        """
        self.refactor(
            "rename-method", target="Customer::get_inv_cdtlmt", new_name="get_invoice_credit_limit"
        )

    def test_name_conflict(self) -> None:
        """Test rename method when a method with the target name already exists.

        This is an edge case where renaming to the new name could cause a
        conflict with an existing method in the class. The refactoring must
        handle this scenario gracefully by detecting or preventing the conflict.
        """
        self.refactor(
            "rename-method", target="Customer::get_inv_cdtlmt", new_name="get_invoice_credit_limit"
        )

    def test_multi_file(self) -> None:
        """Test rename method when call sites span multiple files.

        This tests the most important real-world scenario: renaming a method
        when it's called from different files in the project. The refactoring
        must update the method definition AND all call sites across:
        - order.py: Method definition and internal self.get_price() call
        - processor.py: External call via order.get_price()
        - utils.py: External calls via order.get_price() parameter

        Uses multi-file fixtures with input/ and expected/ directories.
        """
        self.refactor_directory(
            "rename-method", target="Order::get_price", new_name="calculate_total_price"
        )
