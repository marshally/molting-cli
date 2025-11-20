"""
Tests for Introduce Parameter refactoring.

This module tests the refactoring that adds a new parameter to a method
and updates call sites accordingly.
"""
from tests.conftest import RefactoringTestBase


class TestIntroduceParameter(RefactoringTestBase):
    """Tests for Introduce Parameter refactoring."""
    fixture_category = "simplifying_method_calls/introduce_parameter"

    def test_simple(self):
        """Add a parameter to a method and update all call sites."""
        self.refactor(
            "introduce-parameter",
            target="Calculator::compute",
            name="tax_rate",
            default="0.0"
        )

    def test_without_default(self):
        """Add a parameter without a default value."""
        self.refactor(
            "introduce-parameter",
            target="Calculator::compute",
            name="tax_rate"
        )

    def test_invalid_target(self):
        """Test that invalid target raises an error."""
        import pytest
        from pathlib import Path

        # Create a temporary file
        test_file = self.tmp_path / "test_invalid.py"
        test_file.write_text("class Foo:\n    def bar(self):\n        pass\n")

        # Try to refactor a non-existent method
        from molting.refactorings.simplifying_method_calls.introduce_parameter import IntroduceParameter

        refactor = IntroduceParameter(str(test_file), "Foo::nonexistent", "param")

        with pytest.raises(ValueError, match="Could not find method"):
            refactor.apply(test_file.read_text())
