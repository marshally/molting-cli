"""
Tests for Change Unidirectional Association to Bidirectional refactoring.

This test module verifies the change-unidirectional-association-to-bidirectional refactoring,
which adds back pointers and updates modifiers to maintain bidirectional consistency.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestChangeUnidirectionalAssociationToBidirectional(RefactoringTestBase):
    """Tests for Change Unidirectional Association to Bidirectional refactoring."""

    fixture_category = "organizing_data/change_unidirectional_association_to_bidirectional"

    def test_simple(self) -> None:
        """Test basic conversion of unidirectional association to bidirectional.

        This is the simplest case: adding a back pointer from the referenced class
        back to the referencing class, and ensuring both directions stay synchronized.
        Verifies the core transformation works before testing complex instance variables.
        """
        self.refactor(
            "change-unidirectional-association-to-bidirectional",
            target="Order::customer",
            back="orders",
        )

    def test_with_instance_vars(self) -> None:
        """Test unidirectional-to-bidirectional conversion with complex instance state.

        Unlike test_simple which uses simple references, this verifies that associations
        with multiple instance variables are properly synchronized bidirectionally.
        Currently skipped due to fixture loading issues.
        """
        self.refactor(
            "change-unidirectional-association-to-bidirectional",
            target="Team::manager",
            back="teams",
        )
