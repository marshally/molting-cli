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
        """Turn a reference object into a value object."""
        self.refactor("change-reference-to-value", target="Currency")

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-reference-to-value with instance variables."""
        self.refactor("change-reference-to-value", target="Money")
