"""Tests for RefactoringBase AST navigation helper methods."""

import ast
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


def test_find_class_def():
    """Test finding a class definition by name in an AST."""
    refactoring = ConcreteRefactoring()

    source_code = """
class MyClass:
    def method(self):
        pass

class AnotherClass:
    pass
"""

    tree = ast.parse(source_code)

    # Find existing class
    my_class = refactoring.find_class_def(tree, "MyClass")
    assert my_class is not None
    assert isinstance(my_class, ast.ClassDef)
    assert my_class.name == "MyClass"

    # Find another class
    another_class = refactoring.find_class_def(tree, "AnotherClass")
    assert another_class is not None
    assert isinstance(another_class, ast.ClassDef)
    assert another_class.name == "AnotherClass"

    # Class not found returns None
    not_found = refactoring.find_class_def(tree, "NonExistentClass")
    assert not_found is None


def test_find_method_in_class():
    """Test finding a method in a class by name."""
    refactoring = ConcreteRefactoring()

    source_code = """
class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass

    def method_three(self, arg):
        return arg
"""

    tree = ast.parse(source_code)
    my_class = tree.body[0]  # Get the class node

    # Find existing method
    method_one = refactoring.find_method_in_class(my_class, "method_one")
    assert method_one is not None
    assert isinstance(method_one, ast.FunctionDef)
    assert method_one.name == "method_one"

    # Find another method
    method_three = refactoring.find_method_in_class(my_class, "method_three")
    assert method_three is not None
    assert isinstance(method_three, ast.FunctionDef)
    assert method_three.name == "method_three"

    # Method not found returns None
    not_found = refactoring.find_method_in_class(my_class, "nonexistent_method")
    assert not_found is None
