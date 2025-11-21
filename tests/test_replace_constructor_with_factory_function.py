"""
Tests for Replace Constructor with Factory Function refactoring.

This test module uses TDD to implement the Replace Constructor with Factory Function
refactoring, which replaces direct constructor calls with a factory function.
"""


class TestTargetParsing:
    """Test that target specifications are parsed correctly."""

    def test_parse_class_name_only(self):
        """Test parsing target with just class name."""
        from molting.refactorings.simplifying_method_calls.replace_constructor_with_factory_function import (
            ReplaceConstructorWithFactoryFunction,
        )

        # Create a simple test file
        test_code = """class Employee:
    def __init__(self, employee_type):
        self.type = employee_type
"""
        # This should not raise an error
        refactoring = ReplaceConstructorWithFactoryFunction(
            file_path="/tmp/test.py", target="Employee", source_code=test_code
        )

        assert refactoring.target == "Employee"
        assert refactoring.class_name == "Employee"


class TestFactoryCreation:
    """Test that factory function is created correctly."""

    def test_creates_factory_function(self, tmp_path):
        """Test that factory function is created from a simple class."""
        from molting.refactorings.simplifying_method_calls.replace_constructor_with_factory_function import (
            ReplaceConstructorWithFactoryFunction,
        )

        input_code = """class Employee:
    ENGINEER = 0
    SALESMAN = 1
    MANAGER = 2

    def __init__(self, employee_type):
        self.type = employee_type
"""

        # Create a temporary file
        test_file = tmp_path / "test.py"
        test_file.write_text(input_code)

        refactoring = ReplaceConstructorWithFactoryFunction(
            file_path=str(test_file), target="Employee"
        )

        result = refactoring.apply(input_code)

        # Check that factory function is created
        assert "def create_employee" in result
        assert "return Employee" in result


class TestCLIIntegration:
    """Test CLI integration for the refactoring."""

    def test_cli_command_exists(self):
        """Test that the CLI command is registered."""
        from molting.cli import main

        # Get the CLI group and check for the command
        assert hasattr(main, "commands")
        command_names = list(main.commands.keys())
        assert "replace-constructor-with-factory-function" in command_names
