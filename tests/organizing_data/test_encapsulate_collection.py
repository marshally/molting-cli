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
        """Test basic encapsulate collection on a public collection field.

        This is the simplest case: converting direct collection access to controlled
        access via a read-only getter and add/remove methods. Verifies the core
        transformation before testing classes with existing accessors or decorators.
        """
        self.refactor("encapsulate-collection", target="Person::courses")

    def test_with_decorators(self) -> None:
        """Test encapsulate collection when class has existing decorated accessor methods.

        Unlike test_simple, this verifies that methods with decorators like @property
        are properly handled and don't conflict with the generated collection accessor
        methods. Important for classes that already use Python's property protocol.
        """
        self.refactor("encapsulate-collection", target="Person::courses")

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update external call sites"
    )
    def test_multiple_calls(self) -> None:
        """Test encapsulate collection when collection is accessed from multiple call sites.

        Unlike test_simple, this verifies that all external references to the collection
        are properly updated to use the new accessor methods. This is important to ensure
        that code outside the class still maintains proper encapsulation boundaries.
        Currently skipped as implementation needs to handle updating external call sites.
        """
        self.refactor("encapsulate-collection", target="Person::courses")
