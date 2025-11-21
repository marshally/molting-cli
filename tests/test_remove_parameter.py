"""
Tests for Remove Parameter refactoring.

This module tests refactorings that remove unused parameters from function/method signatures.
"""
import pytest
from tests.conftest import RefactoringTestBase


class TestRemoveParameter(RefactoringTestBase):
    """Tests for Remove Parameter refactoring."""
    fixture_category = "simplifying_method_calls/remove_parameter"

    def test_simple(self):
        """Remove a parameter from a class method."""
        self.refactor(
            "remove-parameter",
            target="Order::calculate_total",
            parameter="discount_code"
        )

    def test_remove_from_middle(self):
        """Remove a parameter from the middle of parameter list."""
        self.refactor(
            "remove-parameter",
            target="calculate",
            parameter="old_param"
        )

    def test_remove_parameter_invalid_target(self):
        """Raise error when target function does not exist."""
        from molting.cli import refactor_file
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def calculate(x, y):\n    return x + y\n")

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "remove-parameter",
                    str(test_file),
                    target="nonexistent_function",
                    parameter="x"
                )

    def test_remove_parameter_nonexistent_parameter(self):
        """Raise error when parameter does not exist."""
        from molting.cli import refactor_file
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def calculate(x, y):\n    return x + y\n")

            with pytest.raises(ValueError, match="Parameter 'z' not found"):
                refactor_file(
                    "remove-parameter",
                    str(test_file),
                    target="calculate",
                    parameter="z"
                )
