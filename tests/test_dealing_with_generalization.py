"""
Tests for Dealing with Generalization refactorings.

This module tests refactorings that manage inheritance hierarchies and relationships
between classes, including pulling up/pushing down fields and methods, extracting
superclasses and subclasses, collapsing hierarchies, and converting between
inheritance and delegation patterns.
"""

from tests.conftest import RefactoringTestBase


class TestPushDownMethod(RefactoringTestBase):
    """Tests for Push Down Method refactoring."""

    fixture_category = "dealing_with_generalization/push_down_method"

    def test_simple(self):
        """Move a method from superclass to those subclasses that need it."""
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")
