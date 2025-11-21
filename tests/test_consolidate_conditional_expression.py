"""
Tests for Consolidate Conditional Expression refactoring.

This module tests the Consolidate Conditional Expression refactoring that combines
a sequence of conditional checks with the same result into a single conditional.
"""

import pytest
from click.testing import CliRunner

from tests.conftest import RefactoringTestBase


class TestConsolidateConditionalExpression(RefactoringTestBase):
    """Tests for Consolidate Conditional Expression refactoring."""

    fixture_category = "simplifying_conditionals/consolidate_conditional_expression"

    def test_simple(self):
        """Combine multiple if statements with same action (return 0) using OR logic."""
        self.refactor("consolidate-conditional-expression", target="disability_amount#L2-L7")

    def test_class_method(self):
        """Combine multiple if statements in a class method."""
        self.refactor("consolidate-conditional-expression", target="Order::get_discount#L3-L8")

    def test_nested_conditions(self):
        """Combine three conditions that all return None."""
        self.refactor("consolidate-conditional-expression", target="process_data#L2-L7")

    def test_no_consolidation_with_else(self):
        """Don't consolidate if statements with else clauses."""
        self.refactor("consolidate-conditional-expression", target="calculate#L2-L7")


class TestConsolidateConditionalExpressionInvalidTargets:
    """Tests for invalid target handling."""

    def test_invalid_target_format(self):
        """Test that invalid target format raises an error."""
        from molting.refactorings.simplifying_conditionals.consolidate_conditional_expression import (
            ConsolidateConditionalExpression,
        )

        with pytest.raises(ValueError, match="Invalid target format"):
            ConsolidateConditionalExpression("dummy.py", "invalid_target")


class TestConsolidateConditionalExpressionCLI:
    """Tests for consolidate-conditional-expression CLI command."""

    def test_cli_command_exists(self):
        """Test that the consolidate-conditional-expression CLI command is registered."""
        from molting.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["consolidate-conditional-expression", "--help"])

        # The command should exist and display help
        assert result.exit_code == 0
        assert (
            "consolidate-conditional-expression" in result.output or "Consolidate" in result.output
        )
