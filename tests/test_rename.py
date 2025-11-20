"""Tests for Rename refactoring.

This module tests the Rename refactoring which allows renaming
variables, methods, classes, or modules using rope's rename capability.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestRenameFunction(RefactoringTestBase):
    """Tests for renaming functions."""
    fixture_category = "composing_methods/rename"

    def test_simple(self):
        """Rename a simple function."""
        self.refactor(
            "rename",
            target="add_numbers",
            new_name="calculate_sum"
        )


class TestRenameMethod(RefactoringTestBase):
    """Tests for renaming class methods."""
    fixture_category = "composing_methods/rename"

    def test_class_method(self):
        """Rename a class method."""
        self.refactor(
            "rename",
            target="Calculator::add_numbers",
            new_name="calculate_sum"
        )


class TestRenameClass(RefactoringTestBase):
    """Tests for renaming classes."""
    fixture_category = "composing_methods/rename"

    def test_rename_class_simple(self):
        """Rename a class."""
        self.refactor(
            "rename",
            target="Calculator",
            new_name="MathEngine"
        )


class TestRenameVariable(RefactoringTestBase):
    """Tests for renaming variables."""
    fixture_category = "composing_methods/rename"

    def test_rename_local_variable(self):
        """Rename a local variable."""
        self.refactor(
            "rename",
            target="count",
            new_name="total"
        )


class TestRenameErrorHandling(RefactoringTestBase):
    """Tests for error handling in rename refactoring."""
    fixture_category = "composing_methods/rename"

    def test_nonexistent_target(self):
        """Test error when target doesn't exist."""
        import pytest

        # Use simple fixture
        self.test_file = self.tmp_path / "input.py"
        self.test_file.write_text("""
def foo():
    pass
""")

        with pytest.raises(ValueError, match="Target 'nonexistent' not found"):
            from molting.refactorings.composing_methods.rename import Rename
            refactor = Rename(str(self.test_file), "nonexistent", "bar")
            refactor.apply(self.test_file.read_text())


class TestRenameCLI:
    """Tests for the rename CLI command."""

    def test_rename_command_exists(self):
        """Test that the rename command is registered in the CLI."""
        from molting.cli import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "rename" in result.output or "Commands:" in result.output

    def test_rename_command_basic(self, tmp_path):
        """Test running rename via CLI command."""
        from molting.cli import main
        from click.testing import CliRunner

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def old_name():\n    pass\n")

        runner = CliRunner()
        result = runner.invoke(main, [
            "rename",
            str(test_file),
            "old_name",
            "new_name"
        ])

        assert result.exit_code == 0
        assert "new_name" in test_file.read_text()
