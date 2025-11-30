"""
Tests for Hide Delegate refactoring.

This module tests the Hide Delegate refactoring which creates methods on
server to hide the delegate.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestHideDelegate(RefactoringTestBase):
    """Tests for Hide Delegate refactoring."""

    fixture_category = "moving_features/hide_delegate"

    def test_simple(self) -> None:
        """Test creating delegating methods to hide delegate object access.

        This baseline case creates wrapper methods on the server class that forward
        calls to the delegate, hiding the delegate's existence from clients. Verifies
        basic delegation pattern implementation works correctly.
        """
        self.refactor("hide-delegate", target="Person::department")

    def test_multiple_calls(self) -> None:
        """Test hiding a delegate that is accessed from multiple locations in the codebase.

        When a delegate is accessed from many places, all those call sites must be
        updated to use the new delegating methods instead of accessing the delegate
        directly. Tests that all client code is properly updated.
        """
        self.refactor("hide-delegate", target="Person::department")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_with_instance_vars(self) -> None:
        """Test hiding a delegate where the delegate object is an instance variable.

        Unlike test_simple which may access a simpler delegate, this tests hiding
        delegates that are stored as instance variables and may have complex
        initialization or state relationships with the server class.
        """
        self.refactor("hide-delegate", target="Employee::compensation")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_with_decorators(self) -> None:
        """Test hiding a delegate that is accessed via decorated properties.

        When delegate access is through decorated properties (e.g., @property),
        the refactoring must handle decorator preservation and ensure delegating
        methods work correctly with property syntax.
        """
        self.refactor("hide-delegate", target="Employee::compensation")

    def test_name_conflict(self) -> None:
        """Test that hide delegate raises error when delegating method name exists.

        This error handling test verifies the refactoring detects when a method
        with the same name as the delegating method already exists on the server class.
        Prevents silent overwriting of existing methods.
        """
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("hide-delegate", target="Person::department")
