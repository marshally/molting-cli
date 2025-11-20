"""
Tests for Introduce Assertion refactoring.

This module tests the Introduce Assertion refactoring that makes assumptions
explicit with assertions.
"""
from tests.conftest import RefactoringTestBase


class TestIntroduceAssertion(RefactoringTestBase):
    """Tests for Introduce Assertion refactoring."""
    fixture_category = "simplifying_conditionals/introduce_assertion"

    def test_simple(self):
        """Make assumptions explicit with an assertion."""
        self.refactor(
            "introduce-assertion",
            target="get_expense_limit#L3",
            condition="project.expense_limit is not None or project.primary_project is not None",
            message="Project must have expense limit or primary project"
        )

    def test_simple_condition(self):
        """Insert assert with simple condition (x != 0)."""
        self.refactor(
            "introduce-assertion",
            target="divide#L2",
            condition="b != 0",
            message="b must not be zero"
        )

    def test_complex_condition(self):
        """Insert assert with complex condition (x > 0 and y < 100)."""
        self.refactor(
            "introduce-assertion",
            target="calculate#L2",
            condition="x > 0 and y < 100",
            message="x must be positive and y must be less than 100"
        )

    def test_invalid_target_format(self):
        """Test that invalid target format raises an error."""
        import pytest
        from pathlib import Path
        import tempfile
        from molting.refactorings.simplifying_conditionals.introduce_assertion import IntroduceAssertion

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_func():\n    pass\n")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="Invalid target format"):
                IntroduceAssertion(
                    temp_file,
                    target="divide_without_line",
                    condition="b != 0"
                )
        finally:
            Path(temp_file).unlink()
