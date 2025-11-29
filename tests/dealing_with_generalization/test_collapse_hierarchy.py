"""
Tests for Collapse Hierarchy refactoring.

This refactoring merges a subclass into its superclass when the inheritance
hierarchy is no longer needed.
"""

from tests.conftest import RefactoringTestBase


class TestCollapseHierarchy(RefactoringTestBase):
    """Tests for Collapse Hierarchy refactoring."""

    fixture_category = "dealing_with_generalization/collapse_hierarchy"

    def test_simple(self) -> None:
        """Test basic merging of a subclass into its superclass.

        Merges the Salesman subclass into the Employee superclass, moving all
        of Salesman's features (fields and methods) into Employee and removing
        the now-redundant subclass. This is the simplest case: collapsing an
        inheritance hierarchy that is no longer needed.
        """
        self.refactor("collapse-hierarchy", target="Salesman", into="Employee")
