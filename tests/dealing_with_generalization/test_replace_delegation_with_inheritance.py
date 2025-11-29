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
        """Make the delegating class a subclass of the delegate."""
        self.refactor("replace-delegation-with-inheritance", target="Employee", delegate="_person")

    @pytest.mark.skip(reason="Implementation needed for instance variables")
    def test_with_instance_vars(self) -> None:
        """Test replace-delegation-with-inheritance with instance variables."""
        self.refactor("replace-delegation-with-inheritance", target="Employee", delegate="_contact")
