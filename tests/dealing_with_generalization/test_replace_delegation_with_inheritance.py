"""
Tests for Replace Delegation with Inheritance refactoring.

This refactoring replaces delegation with inheritance by making the
delegating class a subclass of the delegate.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceDelegationWithInheritance(RefactoringTestBase):
    """Tests for Replace Delegation with Inheritance refactoring."""

    fixture_category = "dealing_with_generalization/replace_delegation_with_inheritance"

    def test_simple(self) -> None:
        """Test basic conversion from delegation to inheritance.

        Converts Employee from delegating to a _person field into inheriting from
        the Person class. All delegation calls are replaced with inherited method
        access. This is the simplest case: a straightforward delegation pattern
        with no special complications.
        """
        self.refactor("replace-delegation-with-inheritance", target="Employee", delegate="_person")

    def test_with_instance_vars(self) -> None:
        """Test replace-delegation-with-inheritance with instance variables.

        Unlike test_simple, this tests the refactoring when the delegating class
        (Employee) has its own instance variables that need to coexist with the
        inherited state. This is more complex because the instance state must be
        properly initialized through the inheritance chain.
        """
        self.refactor("replace-delegation-with-inheritance", target="Employee", delegate="_contact")
