"""
Tests for Remove Setting Method refactoring.

This module tests refactorings that remove setter methods from classes.
"""
import pytest
from tests.conftest import RefactoringTestBase


class TestRemoveSettingMethod(RefactoringTestBase):
    """Tests for Remove Setting Method refactoring."""
    fixture_category = "simplifying_method_calls/remove_setting_method"

    def test_simple(self):
        """Remove a simple setter method from a class."""
        self.refactor(
            "remove-setting-method",
            target="Account::set_id"
        )

    def test_set_field_pattern(self):
        """Remove a setter method that follows the set_field pattern."""
        self.refactor(
            "remove-setting-method",
            target="User::set_name"
        )

    def test_property_setter(self):
        """Remove a property setter decorated with @property.setter."""
        self.refactor(
            "remove-setting-method",
            target="Product::price"
        )

    def test_invalid_target_nonexistent_method(self):
        """Raise error when target method does not exist."""
        from molting.cli import refactor_file
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("""class Employee:
    def __init__(self, id):
        self._id = id

    def get_id(self):
        return self._id
""")

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "remove-setting-method",
                    str(test_file),
                    target="Employee::nonexistent_method"
                )

    def test_invalid_target_format(self):
        """Raise error when target format is invalid."""
        from molting.refactorings.simplifying_method_calls.remove_setting_method import RemoveSettingMethod
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def foo():\n    pass\n")

            with pytest.raises(ValueError, match="Invalid target format"):
                RemoveSettingMethod(str(test_file), "invalid_target")
