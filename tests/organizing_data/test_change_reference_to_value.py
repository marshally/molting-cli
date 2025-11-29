"""
Tests for Change Reference to Value refactoring.

This test module verifies the change-reference-to-value refactoring,
which converts a reference object into a value object.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestChangeReferenceToValue(RefactoringTestBase):
    """Tests for Change Reference to Value refactoring."""

    fixture_category = "organizing_data/change_reference_to_value"

    def test_simple(self) -> None:
        """Test basic conversion of a reference object to a value object.

        This is the simplest case: converting a reference type (with identity-based
        equality) into a value type (with value-based equality). Verifies the core
        transformation works before testing objects with instance variables.
        """
        self.refactor("change-reference-to-value", target="Currency")

    def test_with_instance_vars(self) -> None:
        """Test reference-to-value conversion with instance variables and complex state.

        Unlike test_simple which uses a simple reference object, this verifies that
        objects with multiple instance variables are properly converted to value objects
        with correct equality and hashing behavior. Currently skipped due to fixture loading issues.
        """
        self.refactor("change-reference-to-value", target="Money")
