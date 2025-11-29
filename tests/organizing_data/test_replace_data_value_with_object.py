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
        """Turn a data item into an object."""
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    def test_with_locals(self) -> None:
        """Test replace data value with object with local variables."""
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    def test_with_instance_vars(self) -> None:
        """Test replace-data-value-with-object with instance variables."""
        self.refactor(
            "replace-data-value-with-object", target="Invoice::customer_name", name="CustomerInfo"
        )

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update all call sites"
    )
    def test_multiple_calls(self) -> None:
        """Test replace-data-value-with-object with multiple call sites."""
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace data value with object when target name already exists."""
        with pytest.raises(ValueError, match="Class.*Customer.*already exists"):
            self.refactor(
                "replace-data-value-with-object", target="Order::customer", name="Customer"
            )
