"""Tests for Consolidate Duplicate Conditional Fragments refactoring.

This module tests the consolidate-duplicate-conditional-fragments refactoring
that moves identical code appearing in all branches of a conditional outside
the conditional.
"""

import pytest
from click.testing import CliRunner

from molting.refactorings.simplifying_conditionals.consolidate_duplicate_conditional_fragments import (
    ConsolidateDuplicateConditionalFragments,
)
from tests.conftest import RefactoringTestBase


class TestParseTarget:
    """Test parsing of target specifications."""

    def test_parse_function_with_line_number(self):
        """Parse function name with line number format: function_name#L2."""
        refactoring = ConsolidateDuplicateConditionalFragments("/tmp/test.py", "process_order#L2")
        assert refactoring.function_name == "process_order"
        assert refactoring.line_number == 2
        assert refactoring.class_name is None

    def test_parse_class_method_with_line_number(self):
        """Parse class method with line number format: ClassName::method_name#L2."""
        refactoring = ConsolidateDuplicateConditionalFragments(
            "/tmp/test.py", "Order::calculate_total#L3"
        )
        assert refactoring.function_name == "calculate_total"
        assert refactoring.class_name == "Order"
        assert refactoring.line_number == 3

    def test_parse_invalid_target_format(self):
        """Raise ValueError for invalid target format."""
        with pytest.raises(ValueError, match="Invalid target format"):
            ConsolidateDuplicateConditionalFragments("/tmp/test.py", "invalid_target")

    def test_parse_invalid_line_number(self):
        """Raise ValueError for non-numeric line number."""
        with pytest.raises(ValueError, match="Invalid target format"):
            ConsolidateDuplicateConditionalFragments("/tmp/test.py", "function_name#Lnotanumber")


class TestConsolidateDuplicateConditionalFragments(RefactoringTestBase):
    """Tests for Consolidate Duplicate Conditional Fragments refactoring."""

    fixture_category = "simplifying_conditionals/consolidate_duplicate_conditional_fragments"

    def test_simple(self):
        """Consolidate duplicate code at the end of both branches."""
        self.refactor("consolidate-duplicate-conditional-fragments", target="process_order#L2")

    def test_duplicate_at_start(self):
        """Consolidate duplicate code at the start of both branches."""
        self.refactor("consolidate-duplicate-conditional-fragments", target="process_order#L2")

    def test_class_method(self):
        """Consolidate duplicate code in a class method."""
        self.refactor(
            "consolidate-duplicate-conditional-fragments", target="Order::calculate_total#L3"
        )


class TestConsolidateDuplicateConditionalFragmentsCLI:
    """Tests for consolidate-duplicate-conditional-fragments CLI command."""

    def test_cli_command_exists(self):
        """Test that the consolidate-duplicate-conditional-fragments CLI command is registered."""
        from molting.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["consolidate-duplicate-conditional-fragments", "--help"])

        # The command should exist and display help
        assert result.exit_code == 0
        assert (
            "consolidate-duplicate-conditional-fragments" in result.output
            or "Consolidate" in result.output
        )

    def test_cli_command_integration(self):
        """Test the consolidate-duplicate-conditional-fragments CLI command executes correctly."""
        import tempfile
        from pathlib import Path

        from molting.cli import main

        # Create a temporary file with code that needs refactoring
        code = """def calculate_price(is_special, price):
    if is_special:
        total = price * 0.95
        send_order()
    else:
        total = price * 0.98
        send_order()
    return total
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["consolidate-duplicate-conditional-fragments", temp_file, "calculate_price#L2"],
            )

            # The command should execute successfully
            assert result.exit_code == 0
            assert "✓ Consolidated duplicate conditional fragments" in result.output

            # Verify the file was modified correctly
            modified_code = Path(temp_file).read_text()
            assert "send_order()" in modified_code
            # Check that send_order() is now outside the if-else
            lines = modified_code.split("\n")
            send_order_line = None
            else_line = None
            for i, line in enumerate(lines):
                if "else:" in line:
                    else_line = i
                if "send_order()" in line:
                    send_order_line = i

            # send_order() should be after the else block
            assert send_order_line is not None
            assert else_line is not None
            assert send_order_line > else_line
        finally:
            Path(temp_file).unlink()
