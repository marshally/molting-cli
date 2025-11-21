"""
Tests for Hide Method refactoring.

This module tests refactorings that hide methods by adding underscore prefix.
"""
import pytest
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestHideMethod(RefactoringTestBase):
    """Tests for Hide Method refactoring."""
    fixture_category = "simplifying_method_calls/hide_method"

    def test_rename_method_with_underscore_prefix(self):
        """Rename a public method to private by adding underscore prefix."""
        self.refactor(
            "hide-method",
            target="Calculator::helper"
        )

    def test_update_multiple_call_sites(self):
        """Update all call sites when hiding a method that is called multiple times."""
        self.refactor(
            "hide-method",
            target="Calculator::compute"
        )

    def test_method_already_private(self):
        """Handle method that already starts with underscore."""
        self.refactor(
            "hide-method",
            target="Calculator::_internal"
        )

    def test_invalid_target_nonexistent_method(self):
        """Raise error when target method does not exist."""
        from molting.cli import refactor_file
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("class Calculator:\n    def add(self, x, y):\n        return x + y\n")

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "hide-method",
                    str(test_file),
                    target="Calculator::nonexistent_method"
                )

    def test_invalid_target_nonexistent_class(self):
        """Raise error when target class does not exist."""
        from molting.cli import refactor_file
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("class Calculator:\n    def add(self, x, y):\n        return x + y\n")

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "hide-method",
                    str(test_file),
                    target="NotAClass::add"
                )

    def test_invalid_target_format(self):
        """Raise error when target format is invalid."""
        from molting.cli import refactor_file
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("class Calculator:\n    def add(self, x, y):\n        return x + y\n")

            with pytest.raises(ValueError, match="Invalid target format"):
                refactor_file(
                    "hide-method",
                    str(test_file),
                    target="just_a_function"
                )

    def test_complex_method_calls(self):
        """Hide method with complex call patterns in multiple methods."""
        self.refactor(
            "hide-method",
            target="DataProcessor::validate"
        )

    def test_cli_command_hide_method(self):
        """Test the CLI command integration for hide-method."""
        from click.testing import CliRunner
        from molting.cli import main
        import tempfile

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text(
                "class Service:\n"
                "    def process(self, data):\n"
                "        return self.validate(data)\n"
                "    def validate(self, data):\n"
                "        return data is not None\n"
            )

            result = runner.invoke(main, [
                "hide-method",
                str(test_file),
                "Service::validate"
            ])

            assert result.exit_code == 0
            assert "Hidden method" in result.output
            assert "Service::validate" in result.output

            # Verify the file was modified correctly
            modified_content = test_file.read_text()
            assert "def _validate" in modified_content
            assert "self._validate" in modified_content
            assert "def validate" not in modified_content
