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
        """Test basic conversion of bidirectional association to unidirectional.

        This is the simplest case: removing a back pointer that is no longer needed,
        simplifying the association to go in one direction. Verifies the core transformation
        works before testing complex instance variables.
        """
        self.refactor(
            "change-bidirectional-association-to-unidirectional", target="Customer::_orders"
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test bidirectional-to-unidirectional conversion with complex instance state.

        Unlike test_simple which removes simple back pointers, this verifies that
        associations with multiple instance variables are properly simplified when
        the back reference is no longer needed. Currently skipped due to fixture loading issues.
        """
        self.refactor(
            "change-bidirectional-association-to-unidirectional", target="Owner::_projects"
        )
