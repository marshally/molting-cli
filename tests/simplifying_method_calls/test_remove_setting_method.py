"""Tests for Remove Setting Method refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestRemoveSettingMethod(RefactoringTestBase):
    """Tests for Remove Setting Method refactoring."""

    fixture_category = "simplifying_method_calls/remove_setting_method"

    def test_simple(self) -> None:
        """Make the field immutable by removing the setter."""
        self.refactor("remove-setting-method", target="Account::_id")

    def test_multiple_calls(self) -> None:
        """Test remove setting method with multiple call sites."""
        self.refactor("remove-setting-method", target="Account::_id")

    def test_with_instance_vars(self) -> None:
        """Test remove setting method with instance variables."""
        self.refactor("remove-setting-method", target="User::_user_id")
