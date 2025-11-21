"""
Tests for Remove Control Flag refactoring.

This module tests the Remove Control Flag refactoring that replaces
control flag variables with break or return statements.
"""
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import RefactoringTestBase


class TestRemoveControlFlagParsing:
    """Tests for target parsing in Remove Control Flag refactoring."""

    def test_parse_function_and_flag_name(self):
        """Test parsing function name and flag variable name from target."""
        import tempfile

        from molting.refactorings.simplifying_conditionals.remove_control_flag import (
            RemoveControlFlag,
        )

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """def check_security(people):
    found = False
    for person in people:
        if not found:
            if person == "Don":
                found = True
    return found
"""
            )
            temp_file = f.name

        try:
            refactor = RemoveControlFlag(temp_file, "check_security::found")
            assert refactor.function_name == "check_security"
            assert refactor.flag_name == "found"
            assert refactor.class_name is None
        finally:
            Path(temp_file).unlink()

    def test_parse_class_method_and_flag(self):
        """Test parsing class method and flag variable name from target."""
        import tempfile

        from molting.refactorings.simplifying_conditionals.remove_control_flag import (
            RemoveControlFlag,
        )

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """class SecurityChecker:
    def check(self, people):
        found = False
        for person in people:
            if not found:
                if person == "Don":
                    found = True
        return found
"""
            )
            temp_file = f.name

        try:
            refactor = RemoveControlFlag(temp_file, "SecurityChecker::check::found")
            assert refactor.class_name == "SecurityChecker"
            assert refactor.function_name == "check"
            assert refactor.flag_name == "found"
        finally:
            Path(temp_file).unlink()

    def test_invalid_target_format(self):
        """Test that invalid target format raises an error."""
        import tempfile

        from molting.refactorings.simplifying_conditionals.remove_control_flag import (
            RemoveControlFlag,
        )

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_func():\n    pass\n")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Invalid target format"):
                RemoveControlFlag(temp_file, "function_without_flag")
        finally:
            Path(temp_file).unlink()


class TestRemoveControlFlagSimple:
    """Tests for simple control flag removal in loops."""

    def test_remove_flag_with_break_in_loop(self):
        """Test replacing flag assignment with break in a for loop."""
        import tempfile

        from molting.refactorings.simplifying_conditionals.remove_control_flag import (
            RemoveControlFlag,
        )

        source_code = """def check_security(people):
    found = False
    for person in people:
        if not found:
            if person == "Don":
                found = True
    return found
"""

        expected_code = """def check_security(people):
    for person in people:
        if person == "Don":
            return True
    return False
"""

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            refactor = RemoveControlFlag(temp_file, "check_security::found")
            result = refactor.apply(source_code)
            # Compare AST structures to ignore formatting differences
            import ast

            assert ast.dump(ast.parse(result)) == ast.dump(ast.parse(expected_code))
        finally:
            Path(temp_file).unlink()

    def test_remove_flag_in_class_method(self):
        """Test removing control flag from a class method."""
        import tempfile

        from molting.refactorings.simplifying_conditionals.remove_control_flag import (
            RemoveControlFlag,
        )

        source_code = """class SecurityChecker:
    def check(self, people):
        found = False
        for person in people:
            if not found:
                if person == "Don":
                    found = True
        return found
"""

        expected_code = """class SecurityChecker:
    def check(self, people):
        for person in people:
            if person == "Don":
                return True
        return False
"""

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            refactor = RemoveControlFlag(temp_file, "SecurityChecker::check::found")
            result = refactor.apply(source_code)
            # Compare AST structures to ignore formatting differences
            import ast

            assert ast.dump(ast.parse(result)) == ast.dump(ast.parse(expected_code))
        finally:
            Path(temp_file).unlink()


class TestRemoveControlFlagEdgeCases:
    """Tests for edge cases in Remove Control Flag refactoring."""

    def test_flag_initialized_to_true(self):
        """Test removing control flag when initialized to True."""
        import tempfile

        from molting.refactorings.simplifying_conditionals.remove_control_flag import (
            RemoveControlFlag,
        )

        source_code = """def check_security(people):
    done = True
    for person in people:
        if done:
            if person == "Don":
                done = False
    return done
"""

        expected_code = """def check_security(people):
    for person in people:
        if person == "Don":
            return False
    return True
"""

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            refactor = RemoveControlFlag(temp_file, "check_security::done")
            result = refactor.apply(source_code)
            # Compare AST structures to ignore formatting differences
            import ast

            assert ast.dump(ast.parse(result)) == ast.dump(ast.parse(expected_code))
        finally:
            Path(temp_file).unlink()


class TestRemoveControlFlagFixtures(RefactoringTestBase):
    """Tests for Remove Control Flag using fixture-based approach."""

    fixture_category = "simplifying_conditionals/remove_control_flag"

    def test_simple_loop(self):
        """Test removing control flag from a simple loop."""
        self.refactor("remove-control-flag", target="check_security::found")

    def test_class_method(self):
        """Test removing control flag from a class method."""
        self.refactor("remove-control-flag", target="SecurityChecker::check::found")

    def test_multiple_conditions(self):
        """Test removing control flag with multiple conditions in loop."""
        self.refactor("remove-control-flag", target="check_security::found")


class TestRemoveControlFlagCLI:
    """Tests for remove-control-flag CLI command."""

    def test_cli_command_registration(self):
        """Test that the remove-control-flag CLI command is registered."""
        from molting.cli import REFACTORING_REGISTRY

        # Check that remove-control-flag is in the registry
        assert "remove-control-flag" in REFACTORING_REGISTRY
        refactoring_class, params = REFACTORING_REGISTRY["remove-control-flag"]
        assert params == ["target"]

    def test_cli_command_help(self):
        """Test that the remove-control-flag CLI command has help text."""
        runner = CliRunner()
        from molting.cli import main

        result = runner.invoke(main, ["remove-control-flag", "--help"])

        # The command should exist and display help
        assert result.exit_code == 0
        assert "remove-control-flag" in result.output or "control flag" in result.output.lower()
