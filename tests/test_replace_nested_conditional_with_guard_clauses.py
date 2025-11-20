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

    def test_class_method(self):
        """Convert nested conditional in a class method."""
        self.refactor(
            "replace-nested-conditional-with-guard-clauses",
            target="Order::get_discount#L3"
        )

    def test_multi_level_nested(self):
        """Convert deeply nested if-else (4 levels) to guard clauses."""
        self.refactor(
            "replace-nested-conditional-with-guard-clauses",
            target="process_status#L2"
        )


class TestReplaceNestedConditionalWithGuardClausesCLI:
    """Tests for replace-nested-conditional-with-guard-clauses CLI command."""

    def test_cli_command_exists(self):
        """Test that the replace-nested-conditional-with-guard-clauses CLI command is registered."""
        from molting.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["replace-nested-conditional-with-guard-clauses", "--help"])

        # The command should exist and display help
        assert result.exit_code == 0
        assert "Replace nested conditionals" in result.output or "guard clauses" in result.output


class TestReplaceNestedConditionalInvalidTargets:
    """Tests for invalid target handling."""

    def test_invalid_target_format(self):
        """Test that invalid target format raises an error."""
        import pytest
        from pathlib import Path
        import tempfile
        from molting.refactorings.simplifying_conditionals.replace_nested_conditional_with_guard_clauses import ReplaceNestedConditionalWithGuardClauses

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_func():\n    pass\n")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Invalid target format"):
                ReplaceNestedConditionalWithGuardClauses(
                    temp_file,
                    target="function_without_line"
                )
        finally:
            Path(temp_file).unlink()
