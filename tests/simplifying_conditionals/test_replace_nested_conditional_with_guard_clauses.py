"""
Tests for Replace Nested Conditional with Guard Clauses refactoring.

This refactoring uses guard clauses for all special cases.
"""

import pytest

from tests.conftest import RefactoringTestBase


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
