"""
Tests for Introduce Assertion refactoring.

This refactoring makes assumptions explicit with an assertion.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceAssertion(RefactoringTestBase):
    """Tests for Introduce Assertion refactoring."""

    fixture_category = "simplifying_conditionals/introduce_assertion"

    def test_simple(self) -> None:
        """Make assumptions explicit with an assertion."""
        self.refactor(
            "introduce-assertion",
            target="get_expense_limit#L3",
            condition="project.expense_limit is not None or project.primary_project is not None",
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test introduce assertion with instance variables."""
        self.refactor(
            "introduce-assertion",
            target="ExpenseManager::get_expense_limit#L10",
            condition="project.expense_limit is not None or project.primary_project is not None",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test introduce assertion with decorated methods."""
        self.refactor(
            "introduce-assertion",
            target="ExpenseManager::expense_limit#L10",
            condition=(
                "self.project.expense_limit is not None "
                "or self.project.primary_project is not None"
            ),
        )
