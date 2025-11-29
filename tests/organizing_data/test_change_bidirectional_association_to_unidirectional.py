"""
Tests for Change Bidirectional Association to Unidirectional refactoring.

This test module verifies the change-bidirectional-association-to-unidirectional refactoring,
which removes back pointers from bidirectional associations.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestChangeBidirectionalAssociationToUnidirectional(RefactoringTestBase):
    """Tests for Change Bidirectional Association to Unidirectional refactoring."""

    fixture_category = "organizing_data/change_bidirectional_association_to_unidirectional"

    def test_simple(self) -> None:
        """Remove back pointers."""
        self.refactor(
            "change-bidirectional-association-to-unidirectional", target="Customer::_orders"
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-bidirectional-association-to-unidirectional with instance variables."""
        self.refactor(
            "change-bidirectional-association-to-unidirectional", target="Owner::_projects"
        )
