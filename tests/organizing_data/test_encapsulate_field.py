"""
Tests for Encapsulate Field refactoring.

This test module verifies the encapsulate-field refactoring,
which makes fields private and provides accessor methods.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestEncapsulateField(RefactoringTestBase):
    """Tests for Encapsulate Field refactoring."""

    fixture_category = "organizing_data/encapsulate_field"

    def test_simple(self) -> None:
        """Make the field private and provide accessors."""
        self.refactor("encapsulate-field", target="Person::name")

    def test_with_decorators(self) -> None:
        """Test encapsulate-field with decorated methods."""
        self.refactor("encapsulate-field", target="Person::name")

    def test_multiple_calls(self) -> None:
        """Test encapsulate-field with multiple call sites."""
        self.refactor("encapsulate-field", target="Person::name")
