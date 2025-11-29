"""
Tests for Replace Inheritance with Delegation refactoring.

This refactoring replaces a subclass with a field containing an instance
of the original superclass, delegating calls to it instead of inheriting.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceInheritanceWithDelegation(RefactoringTestBase):
    """Tests for Replace Inheritance with Delegation refactoring."""

    fixture_category = "dealing_with_generalization/replace_inheritance_with_delegation"

    def test_simple(self) -> None:
        """Test basic replacement of inheritance with delegation.

        Converts a simple inheritance relationship where Stack inherits from
        a collection class into composition: Stack now contains an instance
        of the collection as a field and delegates calls to it instead of
        inheriting. This is the simplest case with no special instance variables.
        """
        self.refactor("replace-inheritance-with-delegation", target="Stack")

    def test_with_instance_vars(self) -> None:
        """Test replace-inheritance-with-delegation with instance variables.

        Unlike test_simple, this tests the refactoring when the inheritance
        hierarchy involves classes with instance variables that need special
        handling during the conversion from inheritance to delegation. This is
        more complex because the instance state must be properly transferred
        to the delegating field.
        """
        self.refactor("replace-inheritance-with-delegation", target="DataStore")
