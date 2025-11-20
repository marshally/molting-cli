"""Tests for Encapsulate Field refactoring.

This module tests the Encapsulate Field refactoring which makes a field
private and provides getter/setter accessors using rope's encapsulate field refactoring.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestEncapsulateFieldSimple(RefactoringTestBase):
    """Tests for encapsulating a simple field."""
    fixture_category = "organizing_data/encapsulate_field"

    def test_simple(self):
        """Encapsulate a simple field with getter and setter."""
        self.refactor(
            "encapsulate-field",
            target="Person::name"
        )
