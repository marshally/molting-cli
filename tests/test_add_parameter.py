"""
Tests for Add Parameter refactoring.

This module tests refactorings that add new parameters to function/method signatures.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestAddParameter(RefactoringTestBase):
    """Tests for Add Parameter refactoring."""

    fixture_category = "simplifying_method_calls/add_parameter"

    def test_add_parameter_to_function(self):
        """Add a parameter to a simple function."""
        self.refactor("add-parameter", target="calculate", name="new_param")

    def test_add_parameter_with_default_value(self):
        """Add a parameter with a default value to a function."""
        self.refactor("add-parameter", target="calculate_total", name="tax_rate", default="0.0")

    def test_add_parameter_to_class_method(self):
        """Add a parameter to a class method."""
        self.refactor("add-parameter", target="Calculator::add", name="precision")

    def test_add_parameter_invalid_target(self):
        """Raise error when target function does not exist."""
        import tempfile
        from pathlib import Path

        from molting.cli import refactor_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def calculate(x, y):\n    return x + y\n")

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "add-parameter",
                    str(test_file),
                    target="nonexistent_function",
                    name="new_param",
                    default=None,
                )

    def test_cli_command_add_parameter(self):
        """Test the CLI command integration for add-parameter."""
        import tempfile
        from pathlib import Path

        from click.testing import CliRunner

        from molting.cli import main

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def greet(name):\n    return f'Hello, {name}!'\n")

            result = runner.invoke(
                main, ["add-parameter", str(test_file), "greet", "greeting", "--default", "Hello"]
            )

            assert result.exit_code == 0
            assert "Added parameter" in result.output
            assert "greeting" in result.output

            # Verify the file was modified correctly
            modified_content = test_file.read_text()
            assert "greeting='Hello'" in modified_content or 'greeting="Hello"' in modified_content
