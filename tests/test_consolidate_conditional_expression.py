"""
Tests for Consolidate Conditional Expression refactoring.

This module tests the Consolidate Conditional Expression refactoring that combines
a sequence of conditional checks with the same result into a single conditional.
"""
from pathlib import Path
from click.testing import CliRunner
from tests.conftest import RefactoringTestBase


class TestConsolidateConditionalExpression(RefactoringTestBase):
    """Tests for Consolidate Conditional Expression refactoring."""
    fixture_category = "simplifying_conditionals/consolidate_conditional_expression"

    def test_simple(self):
        """Combine multiple if statements with same action (return 0) using OR logic."""
        self.refactor(
            "consolidate-conditional-expression",
            target="disability_amount#L2-L7"
        )
