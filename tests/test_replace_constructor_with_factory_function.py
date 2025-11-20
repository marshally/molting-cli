"""
Tests for Replace Constructor with Factory Function refactoring.

This test module uses TDD to implement the Replace Constructor with Factory Function
refactoring, which replaces direct constructor calls with a factory function.
"""
import pytest
from pathlib import Path


class TestTargetParsing:
    """Test that target specifications are parsed correctly."""

    def test_parse_class_name_only(self):
        """Test parsing target with just class name."""
        from molting.refactorings.simplifying_method_calls.replace_constructor_with_factory_function import ReplaceConstructorWithFactoryFunction

        # Create a simple test file
        test_code = """class Employee:
    def __init__(self, employee_type):
        self.type = employee_type
"""
        # This should not raise an error
        refactoring = ReplaceConstructorWithFactoryFunction(
            file_path="/tmp/test.py",
            target="Employee",
            source_code=test_code
        )

        assert refactoring.target == "Employee"
        assert refactoring.class_name == "Employee"
