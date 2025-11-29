"""
Tests for Extract Interface refactoring.

This refactoring creates an interface for a common subset of methods
that multiple classes can implement.
"""

from tests.conftest import RefactoringTestBase


class TestExtractInterface(RefactoringTestBase):
    """Tests for Extract Interface refactoring."""

    fixture_category = "dealing_with_generalization/extract_interface"

    def test_simple(self) -> None:
        """Test basic interface extraction from a single class.

        Creates a new interface with a subset of methods from the target class.
        This is the simplest case: extracting 2 related methods (get_rate and
        has_special_skill) into a new Billable interface. Verifies the core
        interface creation and method extraction works before testing edge cases.
        """
        self.refactor(
            "extract-interface",
            target="Employee",
            methods="get_rate,has_special_skill",
            name="Billable",
        )

    def test_name_conflict(self) -> None:
        """Test extract-interface when target interface name already exists.

        Unlike test_simple, this verifies proper handling when the proposed
        interface name (Billable) conflicts with an existing interface or class
        in the codebase. The refactoring should either raise an appropriate error
        or handle the conflict gracefully.
        """
        self.refactor(
            "extract-interface",
            target="Employee",
            methods="get_rate,has_special_skill",
            name="Billable",
        )
