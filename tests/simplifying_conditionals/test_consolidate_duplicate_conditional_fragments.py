"""
Tests for Consolidate Duplicate Conditional Fragments refactoring.

This refactoring moves duplicate code outside the conditional.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestConsolidateDuplicateConditionalFragments(RefactoringTestBase):
    """Tests for Consolidate Duplicate Conditional Fragments refactoring."""

    fixture_category = "simplifying_conditionals/consolidate_duplicate_conditional_fragments"

    def test_simple(self) -> None:
        """Test moving simple duplicate code outside a conditional.

        This is the simplest case: identical code appears in both branches of an
        if-else statement and is moved outside. Verifies the core consolidation works
        before testing with local variables or instance variables.
        """
        self.refactor("consolidate-duplicate-conditional-fragments", target="process_order#L2-L7")

    def test_with_locals(self) -> None:
        """Test consolidating duplicate code when it uses local variables.

        Unlike test_simple, this tests moving duplicate code that depends on local
        variables. Verifies that variable dependencies and scope are preserved when
        moving code outside the conditional branches.

        NOTE: This test requires a more advanced feature where duplicate function calls
        with differing arguments are consolidated into a single call with a ternary
        expression for the differing argument. Current implementation only handles
        completely identical duplicate statements.
        """
        self.refactor(
            "consolidate-duplicate-conditional-fragments", target="calculate_shipping#L8-L16"
        )

    def test_with_instance_vars(self) -> None:
        """Test consolidating duplicate code in an instance method using self variables.

        This tests moving duplicate code from an instance method where the code uses
        instance variables (self.field). Unlike test_with_locals, instance variables
        remain accessible after moving the code. Important for real-world OOP code.
        """
        self.refactor(
            "consolidate-duplicate-conditional-fragments",
            target="OrderProcessor::process_order#L10-L15",
        )

    @pytest.mark.skip(
        reason="Requires pattern matching infrastructure beyond CallSiteUpdater - "
        "needs to find and replace similar duplicate fragment patterns in other functions"
    )
    def test_multiple_calls(self) -> None:
        """Test consolidating duplicate fragments when method is called from multiple locations.

        This tests the consolidation when the method containing the duplicate code is
        called from multiple places. Ensures the refactoring doesn't break any of the
        calling code that depends on the original conditional behavior.
        """
        self.refactor("consolidate-duplicate-conditional-fragments", target="process_order#L4-L9")

    def test_with_decorators(self) -> None:
        """Test consolidating duplicate code in a method with decorators.

        This tests the consolidation when the containing method has decorators
        (e.g., @property, @cached, @staticmethod, etc.). Verifies that decorators
        on the method don't interfere with consolidating the duplicate code.
        """
        self.refactor(
            "consolidate-duplicate-conditional-fragments",
            target="OrderProcessor::total#L10-L15",
        )
