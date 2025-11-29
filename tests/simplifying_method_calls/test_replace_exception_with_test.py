"""Tests for Replace Exception with Test refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceExceptionWithTest(RefactoringTestBase):
    """Tests for Replace Exception with Test refactoring."""

    fixture_category = "simplifying_method_calls/replace_exception_with_test"

    def test_simple(self) -> None:
        """Change the caller to test first instead of catching exception."""
        self.refactor("replace-exception-with-test", target="get_value_for_period")

    def test_multiple_calls(self) -> None:
        """Test replace exception with test with multiple call sites."""
        self.refactor("replace-exception-with-test", target="get_value_for_period")

    def test_with_instance_vars(self) -> None:
        """Test replace exception with test with instance variables."""
        self.refactor("replace-exception-with-test", target="get_value_at_index")
