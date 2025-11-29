"""
Tests for Remove Middle Man refactoring.

This module tests the Remove Middle Man refactoring which gets the client
to call the delegate directly.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestRemoveMiddleMan(RefactoringTestBase):
    """Tests for Remove Middle Man refactoring."""

    fixture_category = "moving_features/remove_middle_man"

    def test_simple(self) -> None:
        """Test removing delegation methods to expose direct delegate access.

        This baseline case removes delegating methods on the server class, allowing
        clients to access the delegate directly. Verifies the transformation correctly
        eliminates the delegation layer and updates client code appropriately.
        """
        self.refactor("remove-middle-man", target="Person")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_multiple_calls(self) -> None:
        """Test removing delegation when delegating methods are called from multiple locations.

        When delegation methods are called from many different call sites, all those
        references must be updated to call the delegate directly. Tests that the
        refactoring updates all callers systematically.
        """
        self.refactor("remove-middle-man", target="Person")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_with_instance_vars(self) -> None:
        """Test removing delegation when the delegate is an instance variable.

        Unlike test_simple where delegate access may be simpler, this tests removing
        delegating methods for instance variable delegates that may have complex
        initialization patterns or multiple delegation layers.
        """
        self.refactor("remove-middle-man", target="Employee")
