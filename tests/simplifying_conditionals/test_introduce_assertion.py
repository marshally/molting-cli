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
        """Test adding an assertion for a simple assumption in a method.

        This is the simplest case: adding an assert statement to make an implicit
        assumption explicit at the start of a method. Verifies the core transformation
        works before testing with instance variables or decorated methods.
        """
        self.refactor(
            "introduce-assertion",
            target="get_expense_limit#L3",
            condition="project.expense_limit is not None or project.primary_project is not None",
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test adding an assertion in an instance method using self variables.

        Unlike test_simple, this adds an assertion in a class method where the condition
        references instance variables (self.field). Verifies that self is correctly handled
        in the assertion, important for real-world object-oriented code.
        """
        self.refactor(
            "introduce-assertion",
            target="ExpenseManager::get_expense_limit#L10",
            condition="project.expense_limit is not None or project.primary_project is not None",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test adding an assertion in a method with decorators.

        This tests adding an assertion when the containing method has decorators
        (e.g., @property, @cached, @staticmethod, etc.). Verifies that decorators
        are preserved and don't interfere with assertion insertion.
        """
        self.refactor(
            "introduce-assertion",
            target="ExpenseManager::expense_limit#L10",
            condition=(
                "self.project.expense_limit is not None "
                "or self.project.primary_project is not None"
            ),
        )
