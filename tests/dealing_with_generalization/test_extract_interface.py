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
        """Create an interface for a common subset of methods."""
        self.refactor(
            "extract-interface",
            target="Employee",
            methods="get_rate,has_special_skill",
            name="Billable",
        )

    def test_name_conflict(self) -> None:
        """Test extract-interface when target interface name already exists."""
        self.refactor(
            "extract-interface",
            target="Employee",
            methods="get_rate,has_special_skill",
            name="Billable",
        )
