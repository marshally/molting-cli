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


class TestParseQualifiedTarget:
    """Tests for the parse_qualified_target method."""

    def test_parse_qualified_target_with_class_and_method(self):
        """Parse 'ClassName::method_name' format."""
        refactoring = ConcreteRefactoring()
        class_name, method_name = refactoring.parse_qualified_target("MyClass::my_method")

        assert class_name == "MyClass"
        assert method_name == "my_method"

    def test_parse_qualified_target_with_nested_class(self):
        """Parse qualified target with nested class name."""
        refactoring = ConcreteRefactoring()
        class_name, method_name = refactoring.parse_qualified_target("OuterClass::inner_method")

        assert class_name == "OuterClass"
        assert method_name == "inner_method"

    def test_parse_qualified_target_with_multiple_colons(self):
        """Parse when method name contains colon-like patterns (shouldn't happen but handle it)."""
        refactoring = ConcreteRefactoring()
        class_name, method_name = refactoring.parse_qualified_target("MyClass::method::with::parts")

        # Should split only on the first "::" occurrence
        assert class_name == "MyClass"
        assert method_name == "method::with::parts"

    def test_parse_qualified_target_with_underscore_names(self):
        """Parse qualified target with underscores in names."""
        refactoring = ConcreteRefactoring()
        class_name, method_name = refactoring.parse_qualified_target("My_Class::my_method_name")

        assert class_name == "My_Class"
        assert method_name == "my_method_name"

    def test_parse_qualified_target_with_numeric_names(self):
        """Parse qualified target with numbers in names."""
        refactoring = ConcreteRefactoring()
        class_name, method_name = refactoring.parse_qualified_target("Class2::method3")

        assert class_name == "Class2"
        assert method_name == "method3"
