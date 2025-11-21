"""
Tests for Add Parameter refactoring.

This module tests refactorings that add new parameters to function/method signatures.
"""
import pytest
from tests.conftest import RefactoringTestBase


class TestAddParameter(RefactoringTestBase):
    """Tests for Add Parameter refactoring."""
    fixture_category = "simplifying_method_calls/add_parameter"

    def test_add_parameter_to_function(self):
        """Add a parameter to a simple function."""
        self.refactor(
            "add-parameter",
            target="calculate",
            name="new_param"
        )

    def test_add_parameter_with_default_value(self):
        """Add a parameter with a default value to a function."""
        self.refactor(
            "add-parameter",
            target="calculate_total",
            name="tax_rate",
            default="0.0"
        )

    def test_add_parameter_to_class_method(self):
        """Add a parameter to a class method."""
        self.refactor(
            "add-parameter",
            target="Calculator::add",
            name="precision"
        )

    def test_add_parameter_invalid_target(self):
        """Raise error when target function does not exist."""
        from molting.cli import refactor_file
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text("def calculate(x, y):\n    return x + y\n")

            with pytest.raises(ValueError, match="Could not find target"):
                refactor_file(
                    "add-parameter",
                    str(test_file),
                    target="nonexistent_function",
                    name="new_param",
                    default=None
                )
