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
        self.refactor("remove-setting-method", target="Account::set_id")

    def test_set_field_pattern(self):
        """Remove a setter method that follows the set_field pattern."""
        self.refactor("remove-setting-method", target="User::set_name")

    def test_property_setter(self):
        """Remove a property setter decorated with @property.setter."""
        self.refactor("remove-setting-method", target="Product::price")

    def test_invalid_target_nonexistent_method(self):
        """Raise error when target method does not exist."""
        import tempfile
        from pathlib import Path

        from molting.cli import refactor_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text(
                """class Employee:
    def __init__(self, id):
        self._id = id

    def get_id(self):
        return self._id
"""
            )

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "remove-setting-method", str(test_file), target="Employee::nonexistent_method"
                )

    def test_invalid_target_format(self):
        """Raise error when target format is invalid."""
        import tempfile
        from pathlib import Path

        from molting.refactorings.simplifying_method_calls.remove_setting_method import (
            RemoveSettingMethod,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def foo():\n    pass\n")

            with pytest.raises(ValueError, match="Invalid target format"):
                RemoveSettingMethod(str(test_file), "invalid_target")

    def test_cli_command_remove_setting_method(self):
        """Test the CLI command integration for remove-setting-method."""
        import tempfile
        from pathlib import Path

        from click.testing import CliRunner

        from molting.cli import main

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text(
                """class Counter:
    def __init__(self, count):
        self._count = count

    def get_count(self):
        return self._count

    def set_count(self, count):
        self._count = count
"""
            )

            result = runner.invoke(
                main, ["remove-setting-method", str(test_file), "Counter::set_count"]
            )

            assert result.exit_code == 0
            assert "Removed setting method" in result.output
            assert "set_count" in result.output

            # Verify the file was modified correctly - setter should be gone
            modified_content = test_file.read_text()
            assert "set_count" not in modified_content
            assert "get_count" in modified_content  # Getter should remain
