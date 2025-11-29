"""
Tests for Pull Up Constructor Body refactoring.

This refactoring extracts common constructor initialization code from subclasses
and moves it to the superclass constructor.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestPullUpConstructorBody(RefactoringTestBase):
    """Tests for Pull Up Constructor Body refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_constructor_body"

    def test_simple(self) -> None:
        """Create a superclass constructor and call it from subclass constructors."""
        self.refactor("pull-up-constructor-body", target="Manager::__init__", to="Employee")

    def test_with_locals(self) -> None:
        """Test pull up constructor body with local variables."""
        self.refactor("pull-up-constructor-body", target="Manager::__init__", to="Employee")

    def test_name_conflict(self) -> None:
        """Test pull-up-constructor-body when parent already has incompatible constructor."""
        self.refactor("pull-up-constructor-body", target="Manager::__init__", to="Employee")
