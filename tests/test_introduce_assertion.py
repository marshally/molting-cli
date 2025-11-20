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
            condition="project.expense_limit is not None or project.primary_project is not None",
            message="Project must have expense limit or primary project"
        )

    def test_simple_condition(self):
        """Insert assert with simple condition (x != 0)."""
        self.refactor(
            "introduce-assertion",
            target="divide#L2",
            condition="b != 0",
            message="b must not be zero"
        )

    def test_complex_condition(self):
        """Insert assert with complex condition (x > 0 and y < 100)."""
        self.refactor(
            "introduce-assertion",
            target="calculate#L2",
            condition="x > 0 and y < 100",
            message="x must be positive and y must be less than 100"
        )
