"""
Tests for Replace Nested Conditional with Guard Clauses refactoring.

This module tests the Replace Nested Conditional with Guard Clauses refactoring
that converts nested if-else statements to guard clauses with early returns.
"""
from pathlib import Path
from click.testing import CliRunner
from tests.conftest import RefactoringTestBase


class TestReplaceNestedConditionalWithGuardClauses(RefactoringTestBase):
    """Tests for Replace Nested Conditional with Guard Clauses refactoring."""
    fixture_category = "simplifying_conditionals/replace_nested_conditional_with_guard_clauses"

    def test_simple_nested_conditional(self):
        """Convert simple nested if-else to guard clauses."""
        self.refactor(
            "replace-nested-conditional-with-guard-clauses",
            target="get_payment#L2"
        )
