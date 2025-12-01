"""
Tests for Introduce Foreign Method refactoring.

This module tests the Introduce Foreign Method refactoring which creates
method in client with server instance as first arg.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceForeignMethod(RefactoringTestBase):
    """Tests for Introduce Foreign Method refactoring."""

    fixture_category = "moving_features/introduce_foreign_method"

    def test_simple(self) -> None:
        """Test adding a foreign method to a class that you don't own.

        This baseline case creates a method in a client class that takes an instance
        of an external class (that you can't modify) as its first parameter. Verifies
        the method is created in the right place and can be called on the external class.
        """
        self.refactor(
            "introduce-foreign-method",
            target="Report::generate#L7",
            for_class="date",
            name="next_day",
        )

    def test_with_locals(self) -> None:
        """Test creating a foreign method that uses local variables from the client.

        Unlike test_simple which may have simple logic, this tests foreign methods
        that depend on local variables from the calling code. Verifies the refactoring
        correctly captures and passes local state as parameters to the foreign method.
        """
        self.refactor(
            "introduce-foreign-method",
            target="Report::generate#L12",
            for_class="date",
            name="add_days",
        )

    def test_name_conflict(self) -> None:
        """Test that introduce foreign method raises error when method name exists.

        This error handling test verifies the refactoring detects when the proposed
        foreign method name already exists in the client class. Prevents silent
        method overwrites.
        """
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor(
                "introduce-foreign-method",
                target="Report::generate#L7",
                for_class="date",
                name="next_day",
            )
