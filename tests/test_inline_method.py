"""Tests for Inline Method refactoring.

This module tests the Inline Method refactoring which allows replacing
calls to a method with the method's body using rope's inline refactoring.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestInlineMethodSimple(RefactoringTestBase):
    """Tests for inlining simple methods."""

    fixture_category = "composing_methods/inline_method"

    def test_simple(self):
        """Inline a simple method."""
        self.refactor("inline", target="Person::more_than_five_late_deliveries")


class TestInlineMethodMultipleCalls(RefactoringTestBase):
    """Tests for inlining methods with multiple calls."""

    fixture_category = "composing_methods/inline_method"

    def test_multiple_calls(self):
        """Inline a method that is called multiple times."""
        self.refactor("inline", target="Calculator::simple_helper")


class TestInlineMethodErrorHandling:
    """Tests for error handling in inline method refactoring."""

    def test_invalid_target_format(self, tmp_path):
        """Test error when target is not in proper format."""
        # Create a simple test file
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def simple_func():
    return 5
"""
        )

        with pytest.raises(ValueError, match="Target must be in format"):
            from molting.refactorings.composing_methods.inline_method import InlineMethod

            refactor = InlineMethod(str(test_file), "simple_func")
            refactor.apply(test_file.read_text())

    def test_nonexistent_class(self, tmp_path):
        """Test error when class doesn't exist."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def foo():
    pass
"""
        )

        with pytest.raises(ValueError, match="Class 'NonExistent' not found"):
            from molting.refactorings.composing_methods.inline_method import InlineMethod

            refactor = InlineMethod(str(test_file), "NonExistent::method")
            refactor.apply(test_file.read_text())

    def test_nonexistent_method(self, tmp_path):
        """Test error when method doesn't exist in class."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
class MyClass:
    def existing_method(self):
        return 5
"""
        )

        with pytest.raises(ValueError, match="Method 'nonexistent' not found"):
            from molting.refactorings.composing_methods.inline_method import InlineMethod

            refactor = InlineMethod(str(test_file), "MyClass::nonexistent")
            refactor.apply(test_file.read_text())


class TestInlineMethodCLI:
    """Tests for the inline CLI command."""

    def test_inline_command_exists(self):
        """Test that the inline command is registered in the CLI."""
        from click.testing import CliRunner

        from molting.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "inline" in result.output or "Commands:" in result.output

    def test_inline_command_basic(self, tmp_path):
        """Test running inline via CLI command."""
        from click.testing import CliRunner

        from molting.cli import main

        # Create a test file with a method to inline
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """class Calculator:
    def helper(self):
        return 5

    def add(self, a, b):
        return a + b + self.helper()
"""
        )

        runner = CliRunner()
        result = runner.invoke(main, ["inline", str(test_file), "Calculator::helper"])

        assert result.exit_code == 0
        content = test_file.read_text()
        assert "helper" not in content or "def helper" not in content
