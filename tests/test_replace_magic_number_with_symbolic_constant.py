"""Tests for Replace Magic Number with Symbolic Constant refactoring.

This module tests the Replace Magic Number with Symbolic Constant refactoring
which replaces numeric literals with named constants.
"""
import pytest
from pathlib import Path


class TestReplaceMagicNumberParseTarget:
    """Tests for parsing target specifications."""

    def test_parse_line_number_from_target(self, tmp_path):
        """Test extracting line number from target specification."""
        from molting.refactorings.organizing_data.replace_magic_number_with_symbolic_constant import ReplaceMagicNumberWithSymbolicConstant

        test_file = tmp_path / "test.py"
        test_file.write_text("x = 0.05\n")

        refactor = ReplaceMagicNumberWithSymbolicConstant(
            str(test_file),
            "calculate#L1",
            "0.05",
            "TAX_RATE"
        )

        # Should parse the line number correctly
        assert refactor.line_number == 1


class TestReplaceMagicNumberSimpleExpression:
    """Tests for replacing simple magic numbers in expressions."""

    def test_replace_simple_magic_number_in_expression(self, tmp_path):
        """Test replacing a simple numeric literal with a constant."""
        from molting.refactorings.organizing_data.replace_magic_number_with_symbolic_constant import ReplaceMagicNumberWithSymbolicConstant

        test_file = tmp_path / "test.py"
        source = "def calculate_tax(amount):\n    return amount * 0.05\n"
        test_file.write_text(source)

        refactor = ReplaceMagicNumberWithSymbolicConstant(
            str(test_file),
            "calculate_tax#L2",
            "0.05",
            "TAX_RATE"
        )

        result = refactor.apply(source)

        # Should contain the constant declaration
        assert "TAX_RATE = 0.05" in result
        # Should replace the magic number with constant name
        assert "amount * TAX_RATE" in result
        # Should NOT contain the original magic number in the expression
        assert "amount * 0.05" not in result


class TestReplaceMagicNumberMultipleOccurrences:
    """Tests for replacing multiple occurrences of the same magic number."""

    def test_replace_multiple_occurrences_of_same_number(self, tmp_path):
        """Test replacing all instances of the magic number throughout file."""
        from molting.refactorings.organizing_data.replace_magic_number_with_symbolic_constant import ReplaceMagicNumberWithSymbolicConstant

        test_file = tmp_path / "test.py"
        source = """def calculate_tax(amount):
    return amount * 0.05

def calculate_discount(amount):
    return amount * 0.05
"""
        test_file.write_text(source)

        refactor = ReplaceMagicNumberWithSymbolicConstant(
            str(test_file),
            "calculate_tax#L2",
            "0.05",
            "TAX_RATE"
        )

        result = refactor.apply(source)

        # Should contain the constant declaration
        assert "TAX_RATE = 0.05" in result
        # Should replace both occurrences
        assert result.count("TAX_RATE") >= 3  # declaration + 2 uses (first line + one more)
        # Should NOT contain the original magic number in function bodies
        assert "amount * 0.05" not in result
        assert "amount * TAX_RATE" in result
