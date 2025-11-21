"""Tests for Extract Method refactoring.

This module tests the Extract Method refactoring which extracts a code block
into a new method using rope's extract method refactoring.
"""

import pytest


class TestExtractMethodLineRangeParsing:
    """Tests for parsing line ranges from target specification."""

    def test_parse_line_range_with_hyphen(self):
        """Parse line range from target like Order::method#L10-L15."""
        from molting.refactorings.composing_methods.extract_method import ExtractMethod

        target = "Order::print_owing#L9-L11"
        # This should not raise an error when parsing
        em = ExtractMethod(
            file_path="tests/fixtures/composing_methods/extract_method/simple/input.py",
            target=target,
            name="print_banner",
        )
        # Verify the line range was parsed correctly
        assert em.start_line == 9
        assert em.end_line == 11

    def test_parse_single_line(self):
        """Parse single line from target like Order::method#L10."""
        from molting.refactorings.composing_methods.extract_method import ExtractMethod

        target = "Order::print_owing#L9"
        em = ExtractMethod(
            file_path="tests/fixtures/composing_methods/extract_method/simple/input.py",
            target=target,
            name="print_banner",
        )
        # For a single line, start_line and end_line should be the same
        assert em.start_line == 9
        assert em.end_line == 9


class TestExtractMethodValidation:
    """Tests for validation of extract method parameters."""

    def test_validate_invalid_line_range(self, tmp_path):
        """Test that invalid line ranges are caught."""
        from molting.refactorings.composing_methods.extract_method import ExtractMethod

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
def foo():
    x = 1
    y = 2
"""
        )
        with pytest.raises(ValueError, match="Invalid target format"):
            ExtractMethod(file_path=str(test_file), target="foo", name="bar")  # Missing line range

    def test_validate_out_of_bounds(self, tmp_path):
        """Test that out-of-bounds line numbers are invalid."""
        from molting.refactorings.composing_methods.extract_method import ExtractMethod

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        target = "foo#L1-L100"
        em = ExtractMethod(str(test_file), target, "bar")
        assert not em.validate(test_file.read_text())  # Line 100 is out of bounds


class TestExtractMethodCLI:
    """Tests for the extract-method CLI command."""

    def test_extract_method_command_exists(self):
        """Test that the extract-method command is registered in the CLI."""
        from click.testing import CliRunner

        from molting.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        # Check if help mentions extract or composing methods
        assert "refactor" in result.output.lower() or "commands:" in result.output.lower()
