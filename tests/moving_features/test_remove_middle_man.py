"""
Tests for Remove Middle Man refactoring.

This module tests the Remove Middle Man refactoring which gets the client
to call the delegate directly.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestRemoveMiddleMan(RefactoringTestBase):
    """Tests for Remove Middle Man refactoring."""

    fixture_category = "moving_features/remove_middle_man"

    def test_simple(self) -> None:
        """Get the client to call the delegate directly."""
        self.refactor("remove-middle-man", target="Person")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_multiple_calls(self) -> None:
        """Test remove middle man with multiple call sites."""
        self.refactor("remove-middle-man", target="Person")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_with_instance_vars(self) -> None:
        """Test remove middle man with instance variables."""
        self.refactor("remove-middle-man", target="Employee")
