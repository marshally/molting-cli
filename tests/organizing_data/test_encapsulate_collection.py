"""
Tests for Encapsulate Collection refactoring.

This test module verifies the encapsulate-collection refactoring,
which provides read-only views and add/remove methods for collections.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestEncapsulateCollection(RefactoringTestBase):
    """Tests for Encapsulate Collection refactoring."""

    fixture_category = "organizing_data/encapsulate_collection"

    def test_simple(self) -> None:
        """Make the method return a read-only view and provide add/remove methods."""
        self.refactor("encapsulate-collection", target="Person::courses")

    def test_with_decorators(self) -> None:
        """Test encapsulate-collection with decorated methods."""
        self.refactor("encapsulate-collection", target="Person::courses")

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update external call sites"
    )
    def test_multiple_calls(self) -> None:
        """Test encapsulate-collection with multiple call sites."""
        self.refactor("encapsulate-collection", target="Person::courses")
