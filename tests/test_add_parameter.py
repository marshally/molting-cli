"""
Tests for Add Parameter refactoring.

This module tests refactorings that add new parameters to function/method signatures.
"""
from tests.conftest import RefactoringTestBase


class TestAddParameter(RefactoringTestBase):
    """Tests for Add Parameter refactoring."""
    fixture_category = "simplifying_method_calls/add_parameter"

    def test_add_parameter_to_function(self):
        """Add a parameter to a simple function."""
        self.refactor(
            "add-parameter",
            target="calculate",
            name="new_param"
        )
