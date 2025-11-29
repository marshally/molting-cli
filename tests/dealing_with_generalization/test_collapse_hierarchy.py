"""
Tests for Collapse Hierarchy refactoring.

This refactoring merges a subclass into its superclass when the inheritance
hierarchy is no longer needed.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestCollapseHierarchy(RefactoringTestBase):
    """Tests for Collapse Hierarchy refactoring."""

    fixture_category = "dealing_with_generalization/collapse_hierarchy"

    def test_simple(self) -> None:
        """Merge a subclass into its superclass."""
        self.refactor("collapse-hierarchy", target="Salesman", into="Employee")
