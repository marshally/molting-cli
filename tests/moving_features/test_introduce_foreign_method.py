"""
Tests for Introduce Foreign Method refactoring.

This module tests the Introduce Foreign Method refactoring which creates method in client with server instance as first arg.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceForeignMethod(RefactoringTestBase):
    """Tests for Introduce Foreign Method refactoring."""

    fixture_category = "moving_features/introduce_foreign_method"

    def test_simple(self) -> None:
        """Create method in client with server instance as first arg."""
        self.refactor(
            "introduce-foreign-method",
            target="Report::generate#L6",
            for_class="date",
            name="next_day",
        )

    @pytest.mark.skip(reason="Implementation needs local variable handling fix")
    def test_with_locals(self) -> None:
        """Test introduce foreign method with local variables."""
        self.refactor(
            "introduce-foreign-method",
            target="Report::generate#L12",
            for_class="date",
            name="add_days",
        )

    def test_name_conflict(self) -> None:
        """Test introduce foreign method when method name already exists."""
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor(
                "introduce-foreign-method",
                target="Report::generate#L6",
                for_class="date",
                name="next_day",
            )
