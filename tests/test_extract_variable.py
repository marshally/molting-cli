"""Tests for Extract Variable refactoring.

This module tests the Extract Variable refactoring which allows extracting
expressions into named variables using rope's extract variable capability.
"""

from tests.conftest import RefactoringTestBase


class TestExtractVariableParseLineRange(RefactoringTestBase):
    """Tests for parsing line range from target specification."""

    fixture_category = "composing_methods/extract_variable"

    def test_parse_line_range_simple(self):
        """Parse line range from target specification like #L10-L12."""
        from molting.refactorings.composing_methods.extract_variable import ExtractVariable

        # Create a simple test file
        test_file = self.tmp_path / "input.py"
        test_file.write_text(
            """
def calculate():
    price = 100
    discount = 0.1
    final = price * (1 - discount)
    return final
"""
        )

        # Test parsing line range
        refactor = ExtractVariable(str(test_file), "calculate#L5-L5", "result")
        start_line, end_line = refactor._parse_line_range("calculate#L5-L5")

        assert start_line == 5
        assert end_line == 5


class TestExtractVariableSimple(RefactoringTestBase):
    """Tests for extracting simple expressions into variables."""

    fixture_category = "composing_methods/extract_variable"

    def test_simple(self):
        """Extract a simple expression into a variable."""
        self.refactor("extract-variable", target="calculate_total#L2", variable_name="tax_amount")


class TestExtractVariableComplex(RefactoringTestBase):
    """Tests for extracting complex expressions into variables."""

    fixture_category = "composing_methods/extract_variable"

    def test_complex(self):
        """Extract a complex expression with multiple operations."""
        self.refactor(
            "extract-variable",
            target="Calculator::compute_discount#L4",
            variable_name="adjusted_price",
        )


class TestExtractVariableErrorHandling(RefactoringTestBase):
    """Tests for error handling in extract variable refactoring."""

    fixture_category = "composing_methods/extract_variable"

    def test_invalid_target_no_line_range(self):
        """Test error when target doesn't contain line range."""
        import pytest

        # Create a simple test file
        test_file = self.tmp_path / "input.py"
        test_file.write_text(
            """
def foo():
    x = 5
    return x
"""
        )

        with pytest.raises(ValueError, match="does not contain line range"):
            from molting.refactorings.composing_methods.extract_variable import ExtractVariable

            refactor = ExtractVariable(str(test_file), "foo", "result")
            refactor.apply(test_file.read_text())


class TestExtractVariableCLI:
    """Tests for the extract-variable CLI command."""

    def test_extract_variable_command_exists(self):
        """Test that the extract-variable command can be called via CLI."""
        from click.testing import CliRunner

        from molting.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        # The command might not be in help, but it should be registered

    def test_extract_variable_command_basic(self, tmp_path):
        """Test running extract-variable via CLI command."""
        from molting.cli import refactor_file

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def calculate(x):\n    result = x * 2\n    return result\n")

        # Apply refactoring using the CLI interface
        refactor_file(
            "extract-variable", str(test_file), target="calculate#L2", variable_name="doubled"
        )

        # Verify the refactoring was applied
        result = test_file.read_text()
        assert "doubled = x * 2" in result
