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
        """Create a field for the superclass and remove the subclassing."""
        self.refactor("replace-inheritance-with-delegation", target="Stack")

    @pytest.mark.skip(reason="Implementation needed for instance variables")
    def test_with_instance_vars(self) -> None:
        """Test replace-inheritance-with-delegation with instance variables."""
        self.refactor("replace-inheritance-with-delegation", target="DataStore")
