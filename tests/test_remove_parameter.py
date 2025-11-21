"""
Tests for Remove Parameter refactoring.

This module tests refactorings that remove unused parameters from function/method signatures.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestRemoveParameter(RefactoringTestBase):
    """Tests for Remove Parameter refactoring."""

    fixture_category = "simplifying_method_calls/remove_parameter"

    def test_simple(self):
        """Remove a parameter from a class method."""
        self.refactor(
            "remove-parameter", target="Order::calculate_total", parameter="discount_code"
        )

    def test_remove_from_middle(self):
        """Remove a parameter from the middle of parameter list."""
        self.refactor("remove-parameter", target="calculate", parameter="old_param")

    def test_remove_first_parameter(self):
        """Remove the first parameter from a parameter list."""
        self.refactor("remove-parameter", target="calculate", parameter="old_param")

    def test_remove_only_parameter(self):
        """Remove the only parameter from a function."""
        self.refactor("remove-parameter", target="process", parameter="unused_param")

    def test_update_call_sites(self):
        """Update call sites when removing a parameter."""
        self.refactor("remove-parameter", target="calculate_total", parameter="old_param")

    def test_remove_parameter_invalid_target(self):
        """Raise error when target function does not exist."""
        import tempfile
        from pathlib import Path

        from molting.cli import refactor_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def calculate(x, y):\n    return x + y\n")

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "remove-parameter", str(test_file), target="nonexistent_function", parameter="x"
                )

    def test_remove_parameter_nonexistent_parameter(self):
        """Raise error when parameter does not exist."""
        import tempfile
        from pathlib import Path

        from molting.cli import refactor_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def calculate(x, y):\n    return x + y\n")

            with pytest.raises(ValueError, match="Parameter 'z' not found"):
                refactor_file("remove-parameter", str(test_file), target="calculate", parameter="z")

    def test_cli_command_remove_parameter(self):
        """Test the CLI command integration for remove-parameter."""
        import tempfile
        from pathlib import Path

        from click.testing import CliRunner

        from molting.cli import main

        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def add(x, y, unused):\n    return x + y\n")

            result = runner.invoke(main, ["remove-parameter", str(test_file), "add", "unused"])

            assert result.exit_code == 0
            assert "Removed parameter" in result.output
            assert "unused" in result.output

            # Verify the file was modified correctly
            modified_content = test_file.read_text()
            assert "def add(x, y):" in modified_content
            assert "unused" not in modified_content
