"""Tests for Separate Query from Modifier refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestSeparateQueryFromModifier(RefactoringTestBase):
    """Tests for Separate Query from Modifier refactoring."""

    fixture_category = "simplifying_method_calls/separate_query_from_modifier"

    def test_simple(self) -> None:
        """Create two methods, one for the query and one for the modification."""
        self.refactor("separate-query-from-modifier", target="Security::get_and_remove_intruder")

    def test_with_decorators(self) -> None:
        """Test separate query from modifier with decorated methods."""
        self.refactor("separate-query-from-modifier", target="TaskQueue::get_and_remove_next")

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test separate query from modifier with multiple call sites."""
        self.refactor("separate-query-from-modifier", target="Security::get_and_remove_intruder")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test separate query from modifier with local variables."""
        self.refactor("separate-query-from-modifier", target="TaskQueue::process_and_get_next")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test separate query from modifier with instance variables."""
        self.refactor(
            "separate-query-from-modifier",
            target="Inventory::get_and_update_lowest_stock",
        )

    def test_name_conflict(self) -> None:
        """Test separate query from modifier when target name already exists."""
        self.refactor("separate-query-from-modifier", target="Security::get_and_remove_intruder")
