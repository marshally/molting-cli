"""
Tests for Change Value to Reference refactoring.

This test module verifies the change-value-to-reference refactoring,
which converts a value object into a reference object.
"""

from tests.conftest import RefactoringTestBase


class TestChangeValueToReference(RefactoringTestBase):
    """Tests for Change Value to Reference refactoring."""

    fixture_category = "organizing_data/change_value_to_reference"

    def test_simple(self) -> None:
        """Test basic conversion of a value object to a reference object.

        This is the simplest case: converting a value type (with value-based equality)
        into a reference type (with identity-based equality). Verifies the core transformation
        works before testing objects with instance variables.
        """
        self.refactor("change-value-to-reference", target="Customer")

    def test_with_instance_vars(self) -> None:
        """Test value-to-reference conversion with complex instance state.

        Unlike test_simple which uses a simple value object, this verifies that
        objects with multiple instance variables are properly converted to reference
        objects with identity-based behavior. Currently skipped due to fixture loading issues.
        """
        self.refactor("change-value-to-reference", target="Product")
