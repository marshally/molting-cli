"""Tests for Inline Temp refactoring.

This module tests the Inline Temp refactoring which allows inlining
temporary variables using rope's inline refactoring capability.
"""
from pathlib import Path
from tests.conftest import RefactoringTestBase


class TestInlineTempSimple(RefactoringTestBase):
    """Tests for inlining simple temporary variables."""
    fixture_category = "composing_methods/inline_temp"

    def test_simple(self):
        """Inline a simple temporary variable."""
        self.refactor(
            "inline-temp",
            target="temp_value"
        )


class TestInlineTempMultipleUses(RefactoringTestBase):
    """Tests for inlining variables with multiple uses."""
    fixture_category = "composing_methods/inline_temp"

    def test_multiple_uses(self):
        """Inline a temporary variable with multiple uses."""
        self.refactor(
            "inline-temp",
            target="base_price"
        )


class TestInlineTempMethodContext(RefactoringTestBase):
    """Tests for inlining variables with method context specification."""
    fixture_category = "composing_methods/inline_temp"

    def test_method_context(self):
        """Inline a temporary variable using method::variable syntax."""
        self.refactor(
            "inline-temp",
            target="Calculator::temp_sum"
        )


class TestInlineTempErrorHandling(RefactoringTestBase):
    """Tests for error handling in inline-temp refactoring."""
    fixture_category = "composing_methods/inline_temp"

    def test_nonexistent_target(self):
        """Test error when target doesn't exist."""
        import pytest

        # Use simple fixture
        self.test_file = self.tmp_path / "input.py"
        self.test_file.write_text("""
def foo():
    x = 1
    return x
""")

        with pytest.raises(ValueError, match="Variable 'nonexistent' not found"):
            from molting.refactorings.composing_methods.inline_temp import InlineTemp
            refactor = InlineTemp(str(self.test_file), "nonexistent")
            refactor.apply(self.test_file.read_text())
