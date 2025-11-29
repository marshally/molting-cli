"""
Tests for Introduce Null Object refactoring.

This refactoring replaces null checks with a null object.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceNullObject(RefactoringTestBase):
    """Tests for Introduce Null Object refactoring."""

    fixture_category = "simplifying_conditionals/introduce_null_object"

    def test_simple(self) -> None:
        """Replace null checks with a null object."""
        self.refactor("introduce-null-object", target_class="Customer")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test introduce null object with instance variables."""
        self.refactor("introduce-null-object", target_class="Customer")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test introduce null object with decorated methods."""
        self.refactor("introduce-null-object", target_class="Customer")
