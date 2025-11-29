"""
Tests for Change Value to Reference refactoring.

This test module verifies the change-value-to-reference refactoring,
which converts a value object into a reference object.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestChangeValueToReference(RefactoringTestBase):
    """Tests for Change Value to Reference refactoring."""

    fixture_category = "organizing_data/change_value_to_reference"

    def test_simple(self) -> None:
        """Turn a value object into a reference object."""
        self.refactor("change-value-to-reference", target="Customer")

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-value-to-reference with instance variables."""
        self.refactor("change-value-to-reference", target="Product")
