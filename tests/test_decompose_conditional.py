"""
Tests for Decompose Conditional refactoring.

This module tests the Decompose Conditional refactoring that extracts
condition and branches into separate methods.
"""
from pathlib import Path
from click.testing import CliRunner
from tests.conftest import RefactoringTestBase


class TestDecomposeConditional(RefactoringTestBase):
    """Tests for Decompose Conditional refactoring."""
    fixture_category = "simplifying_conditionals/decompose_conditional"

    def test_simple(self):
        """Extract condition and branches into separate methods."""
        self.refactor(
            "decompose-conditional",
            target="calculate_charge#L2"
        )

    def test_class_method(self):
        """Extract condition and branches from a class method."""
        self.refactor(
            "decompose-conditional",
            target="Order::get_discount#L3"
        )


class TestDecomposeConditionalCLI:
    """Tests for decompose-conditional CLI command."""

    def test_cli_command_exists(self):
        """Test that the decompose-conditional CLI command is registered."""
        from molting.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["decompose-conditional", "--help"])

        # The command should exist and display help
        assert result.exit_code == 0
        assert "decompose-conditional" in result.output or "Extract" in result.output
