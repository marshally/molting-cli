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
