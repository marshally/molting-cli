"""Tests for VariableFlowAnalyzer."""

import libcst as cst
import pytest

from molting.core.variable_flow_analyzer import VariableFlowAnalyzer


class TestVariableFlowAnalyzer:
    """Test suite for VariableFlowAnalyzer."""

    def test_get_reads_in_range_simple(self):
        """Test detecting variable reads in a line range."""
        code = '''
def process(param):
    x = 10
    y = x + param
    z = y * 2
    return z
'''
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Line 4: y = x + param
        # Should read: x, param
        reads = analyzer.get_reads_in_range(4, 4)
        assert set(reads) == {"x", "param"}

    def test_get_reads_in_range_multiple_lines(self):
        """Test detecting variable reads across multiple lines."""
        code = '''
def calculate():
    a = 5
    b = 10
    c = a + b
    d = c * a
    return d
'''
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "calculate")

        # Lines 5-6: c = a + b; d = c * a
        # Should read: a, b, c
        reads = analyzer.get_reads_in_range(5, 6)
        assert set(reads) == {"a", "b", "c"}
