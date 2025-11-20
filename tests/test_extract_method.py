"""Tests for Extract Method refactoring.

This module tests the Extract Method refactoring which extracts a code block
into a new method using rope's extract method refactoring.
"""
from pathlib import Path
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
            name="print_banner"
        )
        # Verify the line range was parsed correctly
        assert em.start_line == 9
        assert em.end_line == 11
