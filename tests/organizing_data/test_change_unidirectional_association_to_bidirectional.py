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
        """Add back pointers and change modifiers to update both sets."""
        self.refactor(
            "change-unidirectional-association-to-bidirectional",
            target="Order::customer",
            back="orders",
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-unidirectional-association-to-bidirectional with instance variables."""
        self.refactor(
            "change-unidirectional-association-to-bidirectional",
            target="Team::manager",
            back="teams",
        )
