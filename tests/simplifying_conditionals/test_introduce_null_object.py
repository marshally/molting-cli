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
        """Test basic null object pattern implementation on a simple class.

        This is the simplest case: introducing a null object for a class that has
        straightforward null checks. Verifies the core null object pattern works
        before testing with instance variables or decorated methods.
        """
        self.refactor("introduce-null-object", target_class="Customer")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test null object pattern on a class with heavy instance variable usage.

        Unlike test_simple, this tests null object creation when the class has many
        instance variables that need to be initialized in the null object. Tests that
        default values are properly chosen for the null object's state.
        """
        self.refactor("introduce-null-object", target_class="Customer")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test null object pattern on a class whose methods have decorators.

        This tests the null object pattern when the class has decorated methods
        (e.g., @property, @lru_cache, etc.). Verifies the null object correctly
        implements or delegates these decorated methods appropriately.
        """
        self.refactor("introduce-null-object", target_class="Customer")
