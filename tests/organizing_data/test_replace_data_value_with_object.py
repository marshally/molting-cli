"""
Tests for Replace Data Value with Object refactoring.

This test module verifies the replace-data-value-with-object refactoring,
which converts a primitive data value into an object.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceDataValueWithObject(RefactoringTestBase):
    """Tests for Replace Data Value with Object refactoring."""

    fixture_category = "organizing_data/replace_data_value_with_object"

    def test_simple(self) -> None:
        """Test basic replacement of a primitive data value with an object.

        This is the simplest case: converting a primitive field (like a string) into a
        proper object with dedicated behavior. Verifies the core transformation works
        before testing local variables, instance variables, or name conflicts.
        """
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    def test_with_locals(self) -> None:
        """Test data-value-to-object replacement when local variables hold the same data.

        Unlike test_simple which transforms only a field, this verifies that local
        variables holding the same primitive type are also properly converted to the
        new object type throughout the function scope.
        """
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    def test_with_instance_vars(self) -> None:
        """Test data-value-to-object replacement with multiple related instance variables.

        Unlike test_simple which transforms a single field, this verifies that related
        instance variables (like customer_name in Invoice) are properly converted as a
        group into a cohesive object structure.
        """
        self.refactor(
            "replace-data-value-with-object", target="Invoice::customer_name", name="CustomerInfo"
        )

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update all call sites"
    )
    def test_multiple_calls(self) -> None:
        """Test data-value-to-object replacement when value is used in multiple locations.

        Unlike test_simple, this verifies that all external references to the primitive
        value are properly updated to use the new object type. Currently skipped as the
        implementation doesn't yet update all call sites across the codebase.
        """
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test that data-value-to-object replacement fails when class name already exists.

        Unlike test_simple which creates a new class, this verifies proper error handling
        when the requested class name (Customer) would conflict with an existing class.
        This is important to prevent accidental overwriting of existing code.
        Currently skipped as implementation needs to detect and report class name conflicts.
        """
        with pytest.raises(ValueError, match="Class.*Customer.*already exists"):
            self.refactor(
                "replace-data-value-with-object", target="Order::customer", name="Customer"
            )
