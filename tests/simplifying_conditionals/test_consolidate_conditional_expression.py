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
        """Test consolidating multiple simple conditionals with same result.

        This is the simplest case: multiple if conditions that all return the same
        value are combined into a single condition using logical operators. Verifies
        the core consolidation works before testing with local variables or instance variables.
        """
        self.refactor(
            "consolidate-conditional-expression",
            target="disability_amount#L2-L7",
            name="is_not_eligible_for_disability",
        )

    def test_with_locals(self) -> None:
        """Test consolidating conditionals that reference local variables.

        Unlike test_simple, this consolidates conditionals where the conditions
        and/or return values depend on local variables within the method scope.
        Verifies that variable scope and dependencies are preserved during consolidation.
        """
        self.refactor(
            "consolidate-conditional-expression",
            target="calculate_bonus#L9-L15",
            name="is_not_eligible_for_bonus",
        )

    def test_with_instance_vars(self) -> None:
        """Test consolidating conditionals in an instance method using self variables.

        This consolidates conditionals in a class method where the conditions reference
        instance variables (self.field). Unlike test_with_locals, instance variables remain
        accessible without parameter passing. Important for real-world object-oriented code.
        """
        self.refactor(
            "consolidate-conditional-expression",
            target="BenefitsCalculator::disability_amount#L10-L15",
            name="is_not_eligible_for_disability",
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test consolidating conditionals when the desired extracted name already exists.

        This tests a name conflict scenario where the refactoring tool needs to either
        rename the target, skip the consolidation, or handle an existing method with the
        same name. Important for error handling and user feedback in real-world scenarios.
        """
        self.refactor(
            "consolidate-conditional-expression",
            target="disability_amount#L10-L15",
            name="is_not_eligible_for_disability",
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test consolidating conditionals that appear in multiple places in the code.

        This tests consolidation when the same pattern of conditionals appears multiple
        times, or when the extracted method will be called from multiple locations.
        Ensures the consolidation is sound across all uses of the refactored code.
        """
        self.refactor(
            "consolidate-conditional-expression",
            target="disability_amount#L4-L9",
            name="is_not_eligible_for_disability",
        )

    def test_with_decorators(self) -> None:
        """Test consolidating conditionals in a method with decorators.

        This tests consolidation when the containing method has decorators (e.g., @property,
        @cached, @staticmethod, etc.). Verifies that decorators on the method containing
        the conditionals don't interfere with the consolidation logic.
        """
        self.refactor(
            "consolidate-conditional-expression",
            target="EmployeeBenefits::disability_amount#L10-L15",
            name="is_not_eligible_for_disability",
        )
