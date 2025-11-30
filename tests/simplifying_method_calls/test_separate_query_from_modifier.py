"""Tests for Separate Query from Modifier refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestSeparateQueryFromModifier(RefactoringTestBase):
    """Tests for Separate Query from Modifier refactoring."""

    fixture_category = "simplifying_method_calls/separate_query_from_modifier"

    def test_simple(self) -> None:
        """Test separating a query method from a modifier in the basic case.

        This is the simplest case: splitting a method that both queries and
        modifies state (get_and_remove_intruder) into two separate methods
        (get_intruder and remove_intruder). Verifies the core transformation works.
        """
        self.refactor("separate-query-from-modifier", target="Security::get_and_remove_intruder")

    def test_with_decorators(self) -> None:
        """Test separating query from modifier when the method has decorators.

        Unlike test_simple, this tests splitting a decorated method. Decorators
        must be preserved or applied appropriately to the new query and modifier
        methods.
        """
        self.refactor("separate-query-from-modifier", target="TaskQueue::get_and_remove_next")

    @pytest.mark.skip(
        reason="Requires complex statement-level transformation beyond CallSiteUpdater: "
        "1) Replace method calls: get_and_remove_intruder() -> get_intruder(), "
        "2) Insert new statement after: object.remove_intruder(), "
        "3) Requires control flow analysis to determine where to insert the modifier call "
        "(after if blocks when result is used, within loops, etc.). "
        "This needs a sophisticated multi-statement transformer with context awareness."
    )
    def test_multiple_calls(self) -> None:
        """Test separating query from modifier across multiple call sites.

        Unlike test_simple, this verifies that all call sites are updated correctly.
        Some callers may only need the query, others only the modifier, and some
        both. All must be handled appropriately.
        """
        self.refactor("separate-query-from-modifier", target="Security::get_and_remove_intruder")

    @pytest.mark.skip(
        reason="Requires fixing body generation logic - names are swapped. "
        "The command generates correct variable dependencies but assigns "
        "query_body to modifier name and vice versa for process_and_get pattern."
    )
    def test_with_locals(self) -> None:
        """Test separating query from modifier when local variables are involved.

        Unlike test_simple, this tests when the method contains local variable
        definitions. The split must correctly distribute these locals between
        the query and modifier methods.
        """
        self.refactor("separate-query-from-modifier", target="TaskQueue::process_and_get_next")

    def test_with_instance_vars(self) -> None:
        """Test separating query from modifier when instance variables are accessed.

        Unlike test_simple, this tests splitting a method that accesses instance
        variables. Both the query and modifier methods must have correct access
        to the instance state they need.
        """
        self.refactor(
            "separate-query-from-modifier",
            target="Inventory::get_and_update_lowest_stock",
        )

    def test_name_conflict(self) -> None:
        """Test separating query from modifier when new method names would conflict.

        This is an edge case where one of the new methods being created
        (e.g., get_intruder() or remove_intruder()) would conflict with an
        existing method. The refactoring must handle this gracefully.
        """
        self.refactor("separate-query-from-modifier", target="Security::get_and_remove_intruder")
