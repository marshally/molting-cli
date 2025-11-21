"""Tests for RefactoringBase class."""

import pytest
from molting.core.refactoring_base import RefactoringBase


class ConcreteRefactoring(RefactoringBase):
    """Concrete implementation of RefactoringBase for testing."""

    def apply(self, source: str) -> str:
        """Apply the refactoring (stub implementation)."""
        return source

    def validate(self, source: str) -> bool:
        """Validate the refactoring (stub implementation)."""
        return True


class TestParseLineRangeTarget:
    """Tests for parse_line_range_target() method."""

    def test_parse_line_range_target_with_range(self):
        """Test parsing target with line range like 'Order::print_owing#L9-L11'."""
        refactoring = ConcreteRefactoring()
        method_spec, start_line, end_line = refactoring.parse_line_range_target(
            "Order::print_owing#L9-L11"
        )

        assert method_spec == "Order::print_owing"
        assert start_line == 9
        assert end_line == 11

    def test_parse_line_range_target_single_line(self):
        """Test parsing target with single line like 'Order::print_owing#L9'."""
        refactoring = ConcreteRefactoring()
        method_spec, start_line, end_line = refactoring.parse_line_range_target(
            "Order::print_owing#L9"
        )

        assert method_spec == "Order::print_owing"
        assert start_line == 9
        assert end_line == 9

    def test_parse_line_range_target_with_function_only(self):
        """Test parsing target with function name only like 'calculate#L5-L7'."""
        refactoring = ConcreteRefactoring()
        method_spec, start_line, end_line = refactoring.parse_line_range_target(
            "calculate#L5-L7"
        )

        assert method_spec == "calculate"
        assert start_line == 5
        assert end_line == 7

    def test_parse_line_range_target_function_single_line(self):
        """Test parsing target with function name and single line like 'calculate#L5'."""
        refactoring = ConcreteRefactoring()
        method_spec, start_line, end_line = refactoring.parse_line_range_target(
            "calculate#L5"
        )

        assert method_spec == "calculate"
        assert start_line == 5
        assert end_line == 5

    def test_parse_line_range_target_invalid_format(self):
        """Test that invalid target format raises ValueError."""
        refactoring = ConcreteRefactoring()

        with pytest.raises(ValueError, match="Invalid target format"):
            refactoring.parse_line_range_target("invalid_format_no_line")

    def test_parse_line_range_target_missing_line_number(self):
        """Test that missing line number raises ValueError."""
        refactoring = ConcreteRefactoring()

        with pytest.raises(ValueError, match="Invalid target format"):
            refactoring.parse_line_range_target("Order::print_owing#L")

    def test_parse_line_range_target_complex_method_spec(self):
        """Test parsing with complex method specifications like 'Module::Class::method#L10-L20'."""
        refactoring = ConcreteRefactoring()
        method_spec, start_line, end_line = refactoring.parse_line_range_target(
            "Module::Class::method#L10-L20"
        )

        assert method_spec == "Module::Class::method"
        assert start_line == 10
        assert end_line == 20
