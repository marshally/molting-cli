"""
Tests for Simplifying Conditionals refactorings.

This module tests refactorings that simplify and clarify conditional logic.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestDecomposeConditional(RefactoringTestBase):
    """Tests for Decompose Conditional refactoring."""

    fixture_category = "simplifying_conditionals/decompose_conditional"

    def test_simple(self) -> None:
        """Extract the condition and each branch into separate methods."""
        self.refactor("decompose-conditional", target="calculate_charge#L2-L5")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test decompose conditional with local variables."""
        self.refactor("decompose-conditional", target="process_order#L8-L13")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test decompose conditional with instance variables."""
        self.refactor("decompose-conditional", target="PricingCalculator::calculate_charge#L11-L14")

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test decompose conditional with multiple call sites."""
        self.refactor("decompose-conditional", target="calculate_shipping_charge#L5-L8")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test decompose conditional with decorated methods."""
        self.refactor("decompose-conditional", target="PriceCalculator::charge#L14-L17")


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


class TestConsolidateDuplicateConditionalFragments(RefactoringTestBase):
    """Tests for Consolidate Duplicate Conditional Fragments refactoring."""

    fixture_category = "simplifying_conditionals/consolidate_duplicate_conditional_fragments"

    def test_simple(self) -> None:
        """Move duplicate code outside the conditional."""
        self.refactor("consolidate-duplicate-conditional-fragments", target="process_order#L2-L7")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test consolidate duplicate conditional fragments with local variables."""
        self.refactor(
            "consolidate-duplicate-conditional-fragments", target="calculate_shipping#L8-L16"
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test consolidate duplicate conditional fragments with instance variables."""
        self.refactor(
            "consolidate-duplicate-conditional-fragments",
            target="OrderProcessor::process_order#L10-L15",
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test consolidate duplicate conditional fragments with multiple call sites."""
        self.refactor("consolidate-duplicate-conditional-fragments", target="process_order#L4-L9")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test consolidate duplicate conditional fragments with decorated methods."""
        self.refactor(
            "consolidate-duplicate-conditional-fragments",
            target="OrderProcessor::total#L10-L15",
        )


class TestRemoveControlFlag(RefactoringTestBase):
    """Tests for Remove Control Flag refactoring."""

    fixture_category = "simplifying_conditionals/remove_control_flag"

    def test_simple(self) -> None:
        """Replace a control flag variable with break or return."""
        self.refactor("remove-control-flag", target="check_security::found")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test remove control flag with local variables."""
        self.refactor("remove-control-flag", target="find_matching_product::found")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test remove control flag with instance variables."""
        self.refactor("remove-control-flag", target="SecurityChecker::check_security::found")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test remove control flag with decorated methods."""
        self.refactor("remove-control-flag", target="SecurityChecker::is_secure::found")


class TestReplaceNestedConditionalWithGuardClauses(RefactoringTestBase):
    """Tests for Replace Nested Conditional with Guard Clauses refactoring."""

    fixture_category = "simplifying_conditionals/replace_nested_conditional_with_guard_clauses"

    def test_simple(self) -> None:
        """Use guard clauses for all special cases."""
        self.refactor(
            "replace-nested-conditional-with-guard-clauses", target="get_payment_amount#L2-L11"
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test replace nested conditional with guard clauses with instance variables."""
        self.refactor(
            "replace-nested-conditional-with-guard-clauses",
            target="PaymentCalculator::get_payment_amount#L10-L19",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test replace nested conditional with guard clauses with decorated methods."""
        self.refactor(
            "replace-nested-conditional-with-guard-clauses",
            target="PaymentCalculator::payment_amount#L10-L19",
        )


class TestReplaceConditionalWithPolymorphism(RefactoringTestBase):
    """Tests for Replace Conditional with Polymorphism refactoring."""

    fixture_category = "simplifying_conditionals/replace_conditional_with_polymorphism"

    def test_simple(self) -> None:
        """Move each conditional leg to an overriding method in a subclass."""
        self.refactor(
            "replace-conditional-with-polymorphism", target="Employee::pay_amount#L13-L20"
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test replace conditional with polymorphism with heavy instance variable usage."""
        self.refactor(
            "replace-conditional-with-polymorphism",
            target="ShippingCalculator::calculate_cost#L16-L27",
        )


class TestIntroduceNullObject(RefactoringTestBase):
    """Tests for Introduce Null Object refactoring."""

    fixture_category = "simplifying_conditionals/introduce_null_object"

    def test_simple(self) -> None:
        """Replace null checks with a null object."""
        self.refactor("introduce-null-object", target_class="Customer")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test introduce null object with instance variables."""
        self.refactor("introduce-null-object", target_class="Customer")


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
