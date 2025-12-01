"""Tests for VariableLifetimeAnalyzer."""

import libcst as cst

from molting.core.variable_lifetime_analyzer import (
    VariableLifetimeAnalyzer,
)


class TestVariableLifetimeAnalyzer:
    """Test suite for VariableLifetimeAnalyzer."""

    def test_get_first_definition_simple_assignment(self):
        """Test getting first definition line for simple assignment."""
        code = """
def process():
    x = 10
    y = x + 5
    z = y * 2
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        assert analyzer.get_first_definition("x") == 3
        assert analyzer.get_first_definition("y") == 4
        assert analyzer.get_first_definition("z") == 5
        assert analyzer.get_first_definition("nonexistent") is None

    def test_get_last_use(self):
        """Test getting last use line for variables."""
        code = """
def process():
    x = 10
    y = x + 5
    z = y * 2
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        assert analyzer.get_last_use("x") == 4  # Used in y = x + 5
        assert analyzer.get_last_use("y") == 5  # Used in z = y * 2
        assert analyzer.get_last_use("z") == 6  # Used in return z
        assert analyzer.get_last_use("nonexistent") is None

    def test_get_lifetime(self):
        """Test getting full lifetime info for a variable."""
        code = """
def process():
    x = 10
    y = x + 5
    return y
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        lifetime = analyzer.get_lifetime("x")
        assert lifetime is not None
        assert lifetime.name == "x"
        assert lifetime.first_definition == 3
        assert lifetime.last_use == 4
        assert lifetime.scope_start == 2
        assert lifetime.scope_end == 5

    def test_is_used_before(self):
        """Test checking if variable is used before a given line."""
        code = """
def process():
    x = 10
    y = x + 5
    z = x + y
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        assert analyzer.is_used_before("x", 6) is True  # x used at line 4 and 5
        assert analyzer.is_used_before("x", 4) is False  # x not used before line 4
        assert analyzer.is_used_before("y", 6) is True  # y used at line 5
        assert analyzer.is_used_before("z", 7) is True  # z used at line 6

    def test_is_used_after(self):
        """Test checking if variable is used after a given line."""
        code = """
def process():
    x = 10
    y = x + 5
    z = x + y
    return z
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        assert analyzer.is_used_after("x", 3) is True  # x used at lines 4, 5
        assert analyzer.is_used_after("x", 5) is False  # x not used after line 5
        assert analyzer.is_used_after("y", 4) is True  # y used at line 5
        assert analyzer.is_used_after("z", 5) is True  # z used at line 6

    def test_class_method(self):
        """Test analyzing variables in a class method."""
        code = """
class Calculator:
    def process(self):
        x = 10
        y = x + 5
        return y
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, "Calculator", "process")

        assert analyzer.get_first_definition("x") == 4
        assert analyzer.get_last_use("x") == 5

    def test_augmented_assignment(self):
        """Test tracking augmented assignments (+=, etc)."""
        code = """
def process():
    count = 0
    count += 1
    return count
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        assert analyzer.get_first_definition("count") == 3
        # count is used at line 4 (read) and written at line 4 (write)
        assert analyzer.get_last_use("count") == 5  # return count

    def test_for_loop_variable(self):
        """Test tracking for loop variables."""
        code = """
def process(items):
    result = 0
    for item in items:
        result += item
    return result
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        assert analyzer.get_first_definition("result") == 3
        assert analyzer.get_first_definition("item") == 4
        assert analyzer.get_last_use("item") == 5

    def test_get_all_lifetimes(self):
        """Test getting all variable lifetimes."""
        code = """
def process():
    x = 10
    y = x + 5
    return y
"""
        module = cst.parse_module(code)
        analyzer = VariableLifetimeAnalyzer(module, None, "process")

        lifetimes = analyzer.get_all_lifetimes()
        assert len(lifetimes) == 2
        assert "x" in lifetimes
        assert "y" in lifetimes
        assert lifetimes["x"].first_definition == 3
        assert lifetimes["y"].first_definition == 4
