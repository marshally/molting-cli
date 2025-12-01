"""
Tests for Push Down Field refactoring.

This refactoring moves a field from a superclass to those subclasses
that specifically need it.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestPushDownField(RefactoringTestBase):
    """Tests for Push Down Field refactoring."""

    fixture_category = "dealing_with_generalization/push_down_field"

    def test_simple(self) -> None:
        """Test basic push-down of a field from superclass to subclass.

        Moves the quota field from the Employee superclass to only the Salesman
        subclass where it's needed. This is the simplest case: a single field
        with no special complications, moving to one subclass. Verifies the
        core field move operation works before testing edge cases.
        """
        self.refactor("push-down-field", target="Employee::quota", to="Salesman")

    def test_with_instance_vars(self) -> None:
        """Test push-down-field with fields that reference instance variables.

        Unlike test_simple, this tests pushing down commission_rate, which may
        reference other instance variables or have initialization dependencies.
        This verifies that all related variable references are properly updated
        when moving the field to the subclass.
        """
        self.refactor("push-down-field", target="Employee::commission_rate", to="Salesman")

    def test_name_conflict(self) -> None:
        """Test push-down-field when target subclass already has a field with the same name.

        Unlike test_simple, this tests the conflict case where the Salesman
        subclass already defines a quota field. The refactoring should either
        merge the fields appropriately or raise a clear error about the conflict.
        """
        self.refactor("push-down-field", target="Employee::quota", to="Salesman")

    def test_with_decorators(self) -> None:
        """Test push-down-field with decorated property methods.

        Unlike test_simple, this tests fields implemented with @property or other
        decorators. The refactoring must handle the decorator syntax and ensure
        decorated accessors are properly moved or recreated in the subclass.
        """
        self.refactor("push-down-field", target="Employee::sales_target", to="Salesman")

    def test_multiple_calls(self) -> None:
        """Test push-down-field when the field is accessed at multiple call sites.

        Unlike test_simple, this tests that when quota is referenced in multiple
        locations throughout the codebase, all call sites are correctly updated
        to reference the subclass version rather than the parent class version.
        """
        self.refactor("push-down-field", target="Employee::quota", to="Salesman")
