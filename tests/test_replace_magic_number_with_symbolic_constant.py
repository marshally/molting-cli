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
