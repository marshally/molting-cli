"""Tests for Split Temporary Variable refactoring."""

from pathlib import Path
import pytest
import tempfile


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
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(source)
            temp_file = f.name

        try:
            refactor = SplitTemporaryVariable(temp_file, "calculate::temp")

            # Should parse without error
            assert refactor.func_name == "calculate"
            assert refactor.var_name == "temp"
        finally:
            Path(temp_file).unlink()

    def test_detect_multiple_assignments_to_variable(self):
        """Detect when a variable is assigned more than once."""
        from molting.refactorings.composing_methods.split_temporary_variable import SplitTemporaryVariable

        source = """def calculate(a, b):
    temp = a + b
    print(temp)
    temp = a * b
    return temp
"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(source)
            temp_file = f.name

        try:
            refactor = SplitTemporaryVariable(temp_file, "calculate::temp")

            # Validate should detect the multiple assignments
            assert refactor.validate(source)
        finally:
            Path(temp_file).unlink()

    def test_split_two_assignments_simple(self):
        """Split a variable with two assignments into two variables."""
        from molting.refactorings.composing_methods.split_temporary_variable import SplitTemporaryVariable

        source = """def calculate(a, b):
    temp = a + b
    print(temp)
    temp = a * b
    return temp
"""
        expected = """def calculate(a, b):
    temp = a + b
    print(temp)
    temp_2 = a * b
    return temp_2
"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(source)
            temp_file = f.name

        try:
            refactor = SplitTemporaryVariable(temp_file, "calculate::temp")
            result = refactor.apply(source)

            # Compare by parsing both as AST to ignore formatting differences
            import ast
            assert ast.dump(ast.parse(result)) == ast.dump(ast.parse(expected))
        finally:
            Path(temp_file).unlink()
