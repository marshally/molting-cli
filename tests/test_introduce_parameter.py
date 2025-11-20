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
