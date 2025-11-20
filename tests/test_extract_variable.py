"""Tests for Extract Variable refactoring.

This module tests the Extract Variable refactoring which allows extracting
expressions into named variables using rope's extract variable capability.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestExtractVariableParseLineRange(RefactoringTestBase):
    """Tests for parsing line range from target specification."""
    fixture_category = "composing_methods/extract_variable"

    def test_parse_line_range_simple(self):
        """Parse line range from target specification like #L10-L12."""
        from molting.refactorings.composing_methods.extract_variable import ExtractVariable

        # Create a simple test file
        test_file = self.tmp_path / "input.py"
        test_file.write_text("""
def calculate():
    price = 100
    discount = 0.1
    final = price * (1 - discount)
    return final
""")

        # Test parsing line range
        refactor = ExtractVariable(str(test_file), "calculate#L5-L5", "result")
        start_line, end_line = refactor._parse_line_range("calculate#L5-L5")

        assert start_line == 5
        assert end_line == 5
