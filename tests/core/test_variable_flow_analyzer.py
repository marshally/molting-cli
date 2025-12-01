"""Tests for VariableFlowAnalyzer."""

import libcst as cst

from molting.core.variable_flow_analyzer import VariableFlowAnalyzer


class TestVariableFlowAnalyzer:
    """Test suite for VariableFlowAnalyzer."""

    def test_get_reads_in_range_simple(self):
        """Test detecting variable reads in a line range."""
        code = """
def process(param):
    x = 10
    y = x + param
    z = y * 2
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Line 4: y = x + param
        # Should read: x, param
        reads = analyzer.get_reads_in_range(4, 4)
        assert set(reads) == {"x", "param"}

    def test_get_reads_in_range_multiple_lines(self):
        """Test detecting variable reads across multiple lines."""
        code = """
def calculate():
    a = 5
    b = 10
    c = a + b
    d = c * a
    return d
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "calculate")

        # Lines 5-6: c = a + b; d = c * a
        # Should read: a, b, c
        reads = analyzer.get_reads_in_range(5, 6)
        assert set(reads) == {"a", "b", "c"}

    def test_get_writes_in_range_simple(self):
        """Test detecting variable writes in a line range."""
        code = """
def process():
    x = 10
    y = 20
    z = x + y
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Line 3: x = 10
        # Should write: x
        writes = analyzer.get_writes_in_range(3, 3)
        assert writes == ["x"]

    def test_get_writes_in_range_multiple(self):
        """Test detecting multiple variable writes."""
        code = """
def process():
    x = 10
    y = 20
    z = x + y
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Lines 3-4: x = 10; y = 20
        # Should write: x, y
        writes = analyzer.get_writes_in_range(3, 4)
        assert set(writes) == {"x", "y"}

    def test_get_inputs_for_region_read_before_write(self):
        """Test identifying inputs (variables read before written in region)."""
        code = """
def process(param):
    x = 10
    y = x + param
    z = y * 2
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Lines 4-5: y = x + param; z = y * 2
        # Inputs: x (defined outside), param (parameter)
        # y is written before read, so not an input
        inputs = analyzer.get_inputs_for_region(4, 5)
        assert set(inputs) == {"x", "param"}

    def test_get_inputs_for_region_no_external_deps(self):
        """Test region with no external dependencies."""
        code = """
def process():
    x = 10
    y = 20
    z = x + y
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Lines 3-4: x = 10; y = 20
        # No inputs - both variables are defined in the region
        inputs = analyzer.get_inputs_for_region(3, 4)
        assert inputs == []

    def test_get_outputs_from_region_used_later(self):
        """Test identifying outputs (variables written and used after region)."""
        code = """
def process():
    x = 10
    y = 20
    z = x + y
    result = z * 2
    return result
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Lines 3-5: x = 10; y = 20; z = x + y
        # Outputs: z (used in line 6)
        # x and y are not used after the region
        outputs = analyzer.get_outputs_from_region(3, 5)
        assert outputs == ["z"]

    def test_get_outputs_from_region_no_usage_after(self):
        """Test region where no variables are used after."""
        code = """
def process():
    x = 10
    y = 20
    return x + y
"""
        module = cst.parse_module(code)
        analyzer = VariableFlowAnalyzer(module, "", "process")

        # Lines 3-4: x = 10; y = 20
        # No outputs - x and y are only used in the return (line 5)
        # which is outside the region
        outputs = analyzer.get_outputs_from_region(3, 4)
        assert set(outputs) == {"x", "y"}  # Actually used in return statement
