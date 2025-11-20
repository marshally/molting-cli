"""
Tests for Remove Control Flag refactoring.

This module tests the Remove Control Flag refactoring that replaces
control flag variables with break or return statements.
"""
from pathlib import Path
from click.testing import CliRunner
import pytest
from tests.conftest import RefactoringTestBase


class TestRemoveControlFlagParsing:
    """Tests for target parsing in Remove Control Flag refactoring."""

    def test_parse_function_and_flag_name(self):
        """Test parsing function name and flag variable name from target."""
        import tempfile
        from molting.refactorings.simplifying_conditionals.remove_control_flag import RemoveControlFlag

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def check_security(people):
    found = False
    for person in people:
        if not found:
            if person == "Don":
                found = True
    return found
""")
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
        from molting.refactorings.simplifying_conditionals.remove_control_flag import RemoveControlFlag

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""class SecurityChecker:
    def check(self, people):
        found = False
        for person in people:
            if not found:
                if person == "Don":
                    found = True
        return found
""")
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
        from molting.refactorings.simplifying_conditionals.remove_control_flag import RemoveControlFlag

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
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
        from molting.refactorings.simplifying_conditionals.remove_control_flag import RemoveControlFlag

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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
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
