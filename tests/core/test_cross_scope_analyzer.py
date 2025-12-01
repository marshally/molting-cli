"""Tests for CrossScopeAnalyzer."""

import libcst as cst

from molting.core.cross_scope_analyzer import CrossScopeAnalyzer


class TestCrossScopeAnalyzer:
    """Test suite for CrossScopeAnalyzer."""

    def test_get_free_variables_simple(self):
        """Test getting free variables in a simple code region."""
        code = """
def process():
    x = 10
    y = 20
    # Region starts here (line 5)
    result = x + y
    # Region ends here (line 6)
    return result
"""
        module = cst.parse_module(code)
        analyzer = CrossScopeAnalyzer(module, None, "process")

        free_vars = analyzer.get_free_variables(5, 6)
        assert set(free_vars) == {"x", "y"}

    def test_get_free_variables_no_external_deps(self):
        """Test region with no external dependencies."""
        code = """
def process():
    x = 10
    # Region starts here (line 4)
    y = 5
    z = y + 2
    # Region ends here (line 6)
    return x
"""
        module = cst.parse_module(code)
        analyzer = CrossScopeAnalyzer(module, None, "process")

        free_vars = analyzer.get_free_variables(4, 6)
        assert free_vars == []

    def test_needs_closure_true(self):
        """Test detecting when a region needs closure."""
        code = """
def process():
    x = 10
    y = 20
    # Region that uses external variables
    result = x + y
    return result
"""
        module = cst.parse_module(code)
        analyzer = CrossScopeAnalyzer(module, None, "process")

        assert analyzer.needs_closure(5, 6) is True

    def test_needs_closure_false(self):
        """Test detecting when a region doesn't need closure."""
        code = """
def process():
    x = 10
    # Region that is self-contained
    y = 5
    z = y + 2
    return x + z
"""
        module = cst.parse_module(code)
        analyzer = CrossScopeAnalyzer(module, None, "process")

        assert analyzer.needs_closure(4, 6) is False

    def test_get_captured_variables(self):
        """Test getting variables that would be captured."""
        code = """
def process():
    multiplier = 2
    offset = 10
    # Region that would capture multiplier and offset
    result = value * multiplier + offset
    return result
"""
        module = cst.parse_module(code)
        analyzer = CrossScopeAnalyzer(module, None, "process")

        captured = analyzer.get_captured_variables(5, 6)
        assert set(captured) == {"multiplier", "offset", "value"}

    def test_class_method(self):
        """Test analyzing free variables in a class method."""
        code = """
class Calculator:
    def process(self):
        x = 10
        y = 20
        result = x + y
        return result
"""
        module = cst.parse_module(code)
        analyzer = CrossScopeAnalyzer(module, "Calculator", "process")

        free_vars = analyzer.get_free_variables(6, 6)
        assert set(free_vars) == {"x", "y"}
