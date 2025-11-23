"""
Tests for BaseCommand class.

This module tests the core functionality of the BaseCommand class,
including parameter validation and other base functionality.
"""

from pathlib import Path

import pytest

from molting.commands.base import BaseCommand


class ConcreteCommand(BaseCommand):
    """Concrete implementation of BaseCommand for testing."""

    name = "test-command"

    def execute(self) -> None:
        """Execute the refactoring (no-op for testing)."""
        pass

    def validate(self) -> None:
        """Validate parameters (no-op for testing)."""
        pass


class TestValidateRequiredParams:
    """Tests for BaseCommand.validate_required_params() method."""

    def test_all_required_params_present(self) -> None:
        """Should not raise when all required params are present."""
        cmd = ConcreteCommand(
            Path("test.py"), foo="value1", bar="value2", baz="value3"
        )

        # Should not raise
        cmd.validate_required_params("foo", "bar")
        cmd.validate_required_params("foo")
        cmd.validate_required_params("bar", "baz")

    def test_one_missing_param(self) -> None:
        """Should raise ValueError with correct message when one param is missing."""
        cmd = ConcreteCommand(Path("test.py"), foo="value1", bar="value2")

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("foo", "missing_param")

        error_message = str(exc_info.value)
        assert "Missing required parameters for test-command" in error_message
        assert "missing_param" in error_message
        assert "foo" not in error_message  # foo is present, should not be in error

    def test_multiple_missing_params(self) -> None:
        """Should raise ValueError listing all missing params."""
        cmd = ConcreteCommand(Path("test.py"), foo="value1")

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("foo", "missing1", "missing2", "missing3")

        error_message = str(exc_info.value)
        assert "Missing required parameters for test-command" in error_message
        assert "missing1" in error_message
        assert "missing2" in error_message
        assert "missing3" in error_message
        assert "foo" not in error_message  # foo is present, should not be in error

    def test_no_params_required(self) -> None:
        """Should not raise when no params are required."""
        cmd = ConcreteCommand(Path("test.py"), foo="value1")

        # Should not raise
        cmd.validate_required_params()

    def test_no_params_provided_but_some_required(self) -> None:
        """Should raise when params are required but none provided."""
        cmd = ConcreteCommand(Path("test.py"))

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("required_param")

        error_message = str(exc_info.value)
        assert "Missing required parameters for test-command" in error_message
        assert "required_param" in error_message

    def test_error_message_format(self) -> None:
        """Should format error message correctly with comma-separated list."""
        cmd = ConcreteCommand(Path("test.py"))

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("param1", "param2")

        error_message = str(exc_info.value)
        # Check exact format: "Missing required parameters for {name}: {param1}, {param2}"
        assert error_message == "Missing required parameters for test-command: param1, param2"

    def test_includes_command_name_in_error(self) -> None:
        """Should include the command name in the error message."""

        class DifferentCommand(BaseCommand):
            name = "different-command"

            def execute(self) -> None:
                pass

            def validate(self) -> None:
                pass

        cmd = DifferentCommand(Path("test.py"))

        with pytest.raises(ValueError) as exc_info:
            cmd.validate_required_params("missing")

        error_message = str(exc_info.value)
        assert "different-command" in error_message
        assert "test-command" not in error_message
