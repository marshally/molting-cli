"""
Tests for Replace Nested Conditional with Guard Clauses refactoring.

This refactoring uses guard clauses for all special cases.
"""

from tests.conftest import RefactoringTestBase


class TestReplaceNestedConditionalWithGuardClauses(RefactoringTestBase):
    """Tests for Replace Nested Conditional with Guard Clauses refactoring."""

    fixture_category = "simplifying_conditionals/replace_nested_conditional_with_guard_clauses"

    def test_simple(self) -> None:
        """Test replacing nested conditionals with simple guard clauses.

        This is the simplest case: nested if-else statements are refactored to use
        guard clauses to handle edge cases early. Verifies the basic transformation
        works before testing with instance variables or decorated methods.
        """
        self.refactor(
            "replace-nested-conditional-with-guard-clauses", target="get_payment_amount#L2-L11"
        )

    def test_with_instance_vars(self) -> None:
        """Test replacing nested conditionals with guard clauses using instance variables.

        This tests the refactoring in an instance method where the nested conditionals
        reference instance variables (self.field). Verifies that guard clauses correctly
        access instance variables and the transformation preserves method semantics.
        """
        self.refactor(
            "replace-nested-conditional-with-guard-clauses",
            target="PaymentCalculator::get_payment_amount#L10-L19",
        )

    def test_with_decorators(self) -> None:
        """Test replacing nested conditionals with guard clauses on a decorated method.

        This tests the refactoring when the containing method has decorators (e.g., @property,
        @cached, @staticmethod, etc.). Verifies that decorators are preserved and don't
        interfere with the guard clause transformation.
        """
        self.refactor(
            "replace-nested-conditional-with-guard-clauses",
            target="PaymentCalculator::payment_amount#L10-L19",
        )
