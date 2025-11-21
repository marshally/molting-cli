"""
Tests for Remove Parameter refactoring.

This module tests refactorings that remove unused parameters from function/method signatures.
"""
import pytest
from tests.conftest import RefactoringTestBase


class TestRemoveParameter(RefactoringTestBase):
    """Tests for Remove Parameter refactoring."""
    fixture_category = "simplifying_method_calls/remove_parameter"

    def test_simple(self):
        """Remove a parameter from a class method."""
        self.refactor(
            "remove-parameter",
            target="Order::calculate_total",
            parameter="discount_code"
        )
