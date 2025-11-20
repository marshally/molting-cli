"""Tests for Split Temporary Variable refactoring."""

from pathlib import Path
import pytest


class TestSplitTemporaryVariableParsing:
    """Test parsing of split-temporary-variable targets."""

    def test_parse_function_and_variable_from_target(self):
        """Parse function::variable target format correctly."""
        from molting.refactorings.composing_methods.split_temporary_variable import SplitTemporaryVariable

        source = """def calculate(a, b):
    temp = a + b
    print(temp)
    temp = a * b
    return temp
"""
        refactor = SplitTemporaryVariable("dummy.py", "calculate::temp")

        # Should parse without error
        assert refactor.func_name == "calculate"
        assert refactor.var_name == "temp"
