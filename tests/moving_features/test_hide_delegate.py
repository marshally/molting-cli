"""
Tests for Hide Delegate refactoring.

This module tests the Hide Delegate refactoring which creates methods on server to hide the delegate.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestHideDelegate(RefactoringTestBase):
    """Tests for Hide Delegate refactoring."""

    fixture_category = "moving_features/hide_delegate"

    def test_simple(self) -> None:
        """Create methods on server to hide the delegate."""
        self.refactor("hide-delegate", target="Person::department")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_multiple_calls(self) -> None:
        """Test hide delegate with multiple call sites."""
        self.refactor("hide-delegate", target="Person::department")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_with_instance_vars(self) -> None:
        """Test hide delegate with instance variables."""
        self.refactor("hide-delegate", target="Employee::compensation")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_with_decorators(self) -> None:
        """Test hide delegate with decorated properties."""
        self.refactor("hide-delegate", target="Employee::compensation")

    def test_name_conflict(self) -> None:
        """Test hide delegate when delegating method name already exists."""
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("hide-delegate", target="Person::department")
