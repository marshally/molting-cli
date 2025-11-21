"""
Tests for Hide Method refactoring.

This module tests refactorings that hide methods by adding underscore prefix.
"""
import pytest
from tests.conftest import RefactoringTestBase


class TestHideMethod(RefactoringTestBase):
    """Tests for Hide Method refactoring."""
    fixture_category = "simplifying_method_calls/hide_method"

    def test_rename_method_with_underscore_prefix(self):
        """Rename a public method to private by adding underscore prefix."""
        self.refactor(
            "hide-method",
            target="Calculator::helper"
        )

    def test_update_multiple_call_sites(self):
        """Update all call sites when hiding a method that is called multiple times."""
        self.refactor(
            "hide-method",
            target="Calculator::compute"
        )

    def test_method_already_private(self):
        """Handle method that already starts with underscore."""
        self.refactor(
            "hide-method",
            target="Calculator::_internal"
        )
