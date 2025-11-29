"""
Tests for Consolidate Conditional Expression refactoring.

This refactoring combines conditionals with the same result into a single condition.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestConsolidateConditionalExpression(RefactoringTestBase):
    """Tests for Consolidate Conditional Expression refactoring."""

    fixture_category = "simplifying_conditionals/consolidate_conditional_expression"

    def test_simple(self) -> None:
        """Combine conditionals with the same result into a single condition."""
        self.refactor(
            "consolidate-conditional-expression",
            target="disability_amount#L2-L7",
            name="is_not_eligible_for_disability",
        )

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test consolidate conditional expression with local variables."""
        self.refactor(
            "consolidate-conditional-expression",
            target="calculate_bonus#L9-L15",
            name="is_not_eligible_for_bonus",
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test consolidate conditional expression with instance variables."""
        self.refactor(
            "consolidate-conditional-expression",
            target="BenefitsCalculator::disability_amount#L10-L15",
            name="is_not_eligible_for_disability",
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test consolidate conditional expression when target name already exists."""
        self.refactor(
            "consolidate-conditional-expression",
            target="disability_amount#L10-L15",
            name="is_not_eligible_for_disability",
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test consolidate conditional expression with multiple call sites."""
        self.refactor(
            "consolidate-conditional-expression",
            target="disability_amount#L4-L9",
            name="is_not_eligible_for_disability",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test consolidate conditional expression with decorated methods."""
        self.refactor(
            "consolidate-conditional-expression",
            target="EmployeeBenefits::disability_amount#L10-L15",
            name="is_not_eligible_for_disability",
        )
