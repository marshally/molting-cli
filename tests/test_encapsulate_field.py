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


class TestEncapsulateFieldCLI:
    """Tests for the encapsulate-field CLI command."""

    def test_encapsulate_field_command_via_refactor_file(self, tmp_path):
        """Test running encapsulate-field via refactor_file function."""
        from molting.cli import refactor_file

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("class Person:\n    def __init__(self, name):\n        self.name = name\n")

        # Run the refactoring
        refactor_file("encapsulate-field", str(test_file), target="Person::name")

        # Check the result
        result = test_file.read_text()
        assert "_name" in result  # Field should be private
        assert "@property" in result  # Should have property decorator
        assert "def name(self):" in result  # Should have getter
