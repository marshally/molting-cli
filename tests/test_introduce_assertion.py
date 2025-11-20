"""
Tests for Introduce Assertion refactoring.

This module tests the Introduce Assertion refactoring that makes assumptions
explicit with assertions.
"""
from tests.conftest import RefactoringTestBase


class TestIntroduceAssertion(RefactoringTestBase):
    """Tests for Introduce Assertion refactoring."""
    fixture_category = "simplifying_conditionals/introduce_assertion"

    def test_simple(self):
        """Make assumptions explicit with an assertion."""
        self.refactor(
            "introduce-assertion",
            target="get_expense_limit#L3",
            condition="project.expense_limit is not None or project.primary_project is not None"
        )
