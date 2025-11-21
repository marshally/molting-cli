"""
Tests for Remove Setting Method refactoring.

This module tests refactorings that remove setter methods from classes.
"""
import pytest
from tests.conftest import RefactoringTestBase


class TestRemoveSettingMethod(RefactoringTestBase):
    """Tests for Remove Setting Method refactoring."""
    fixture_category = "simplifying_method_calls/remove_setting_method"

    def test_simple(self):
        """Remove a simple setter method from a class."""
        self.refactor(
            "remove-setting-method",
            target="Account::set_id"
        )
