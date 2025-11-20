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


class TestEncapsulateFieldErrorHandling:
    """Tests for error handling in encapsulate-field refactoring."""

    def test_invalid_target_format(self, tmp_path):
        """Test error when target doesn't have ClassName::field_name format."""
        import pytest
        from molting.refactorings.organizing_data.encapsulate_field import EncapsulateField

        test_file = tmp_path / "test.py"
        test_file.write_text("class Person:\n    def __init__(self, name):\n        self.name = name\n")

        with pytest.raises(ValueError, match="Target must be in format"):
            refactor = EncapsulateField(str(test_file), "invalid_target")
            refactor.apply(test_file.read_text())

    def test_class_not_found(self, tmp_path):
        """Test error when target class doesn't exist."""
        import pytest
        from molting.refactorings.organizing_data.encapsulate_field import EncapsulateField

        test_file = tmp_path / "test.py"
        test_file.write_text("class Person:\n    def __init__(self, name):\n        self.name = name\n")

        with pytest.raises(ValueError, match="Class 'NonExistent' not found"):
            refactor = EncapsulateField(str(test_file), "NonExistent::name")
            refactor.apply(test_file.read_text())


class TestEncapsulateFieldMultipleFields:
    """Tests for encapsulating fields in classes with multiple fields."""

    def test_encapsulate_one_field_in_multi_field_class(self, tmp_path):
        """Test encapsulating one field when class has multiple fields."""
        from molting.refactorings.organizing_data.encapsulate_field import EncapsulateField

        test_file = tmp_path / "test.py"
        source = """class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
"""
        test_file.write_text(source)

        # Encapsulate only the name field
        refactor = EncapsulateField(str(test_file), "Person::name")
        result = refactor.apply(source)

        # Check that name is encapsulated
        assert "_name" in result
        assert "@property" in result
        # age should remain unchanged
        assert "self.age = age" in result
