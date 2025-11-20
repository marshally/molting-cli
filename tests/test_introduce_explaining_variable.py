"""
Tests for Introduce Explaining Variable refactoring using strict TDD.

This module implements test-driven development for the Introduce Explaining Variable
refactoring, which extracts complex expressions into named variables for improved
readability.
"""
import pytest
from pathlib import Path
from molting.refactorings.composing_methods.introduce_explaining_variable import IntroduceExplainingVariable


class TestIntroduceExplainingVariableBasicParsing:
    """Test basic target and parameter parsing."""

    def test_parse_simple_target_with_line_number(self, tmp_path):
        """Parse a simple target with function name and line number."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    x = 1\n")

        # Should parse without raising
        refactor = IntroduceExplainingVariable(
            str(test_file),
            target="foo#L2",
            variable_name="result",
            expression="1"
        )

        assert refactor.target == "foo#L2"
        assert refactor.variable_name == "result"
        assert refactor.start_line == 2
        assert refactor.func_name == "foo"

    def test_parse_target_with_class_and_method(self, tmp_path):
        """Parse a target with class::method specification."""
        test_file = tmp_path / "test.py"
        test_file.write_text("class Foo:\n    def bar(self):\n        x = 1\n")

        refactor = IntroduceExplainingVariable(
            str(test_file),
            target="Foo::bar#L3",
            variable_name="result",
            expression="1"
        )

        assert refactor.target == "Foo::bar#L3"
        assert refactor.start_line == 3
        assert refactor.func_name == "bar"

    def test_parse_target_invalid_format_raises_error(self, tmp_path):
        """Invalid target format should raise ValueError."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    x = 1\n")

        with pytest.raises(ValueError):
            IntroduceExplainingVariable(
                str(test_file),
                target="invalid_target_format",
                variable_name="result",
                expression="1"
            )

    def test_validate_returns_true_for_valid_target(self, tmp_path):
        """Validate should return True for valid targets."""
        test_file = tmp_path / "test.py"
        code = "def calculate(x):\n    return x * 2 + 5\n"
        test_file.write_text(code)

        refactor = IntroduceExplainingVariable(
            str(test_file),
            target="calculate#L2",
            variable_name="result",
            expression="x * 2 + 5"
        )

        assert refactor.validate(code) is True

    def test_validate_returns_false_for_line_out_of_bounds(self, tmp_path):
        """Validate should return False when line is out of bounds."""
        test_file = tmp_path / "test.py"
        code = "def foo():\n    x = 1\n"
        test_file.write_text(code)

        refactor = IntroduceExplainingVariable(
            str(test_file),
            target="foo#L100",
            variable_name="result",
            expression="1"
        )

        assert refactor.validate(code) is False


class TestIntroduceExplainingVariableSimpleExtraction:
    """Test extraction of simple expressions."""

    def test_extract_simple_arithmetic_expression(self, tmp_path):
        """Extract a simple arithmetic expression into a variable."""
        test_file = tmp_path / "test.py"
        code = "def calculate(x, y):\n    return x * 2 + y\n"
        test_file.write_text(code)

        refactor = IntroduceExplainingVariable(
            str(test_file),
            target="calculate#L2",
            variable_name="result",
            expression="x * 2 + y"
        )

        result = refactor.apply(code)

        # Should have introduced a variable
        assert "result = " in result
        assert "return result" in result
        # The variable should be assigned before return
        assert result.index("result =") < result.index("return result")

    def test_extract_expression_with_method_call(self, tmp_path):
        """Extract an expression containing method calls."""
        test_file = tmp_path / "test.py"
        code = 'def process(s):\n    return s.upper().replace("A", "B")\n'
        test_file.write_text(code)

        refactor = IntroduceExplainingVariable(
            str(test_file),
            target="process#L2",
            variable_name="processed",
            expression='s.upper().replace("A", "B")'
        )

        result = refactor.apply(code)

        assert "processed = " in result
        assert "return processed" in result
