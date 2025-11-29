"""Tests for Parameterize Method refactoring."""

from tests.conftest import RefactoringTestBase


class TestParameterizeMethod(RefactoringTestBase):
    """Tests for Parameterize Method refactoring."""

    fixture_category = "simplifying_method_calls/parameterize_method"

    def test_simple(self) -> None:
        """Test consolidating two methods with a parameter in the basic case.

        This is the simplest case: combining two similar methods
        (five_percent_raise and ten_percent_raise) into one parameterized
        method (raise_salary). Verifies the core transformation works.
        """
        self.refactor(
            "parameterize-method",
            target1="Employee::five_percent_raise",
            target2="Employee::ten_percent_raise",
            new_name="raise_salary",
        )

    def test_with_decorators(self) -> None:
        """Test parameterizing decorated methods.

        Unlike test_simple, this tests consolidating two decorated methods.
        Decorators must be preserved and applied appropriately to the new
        parameterized method.
        """
        self.refactor(
            "parameterize-method",
            target1="Employee::small_raise",
            target2="Employee::large_raise",
            new_name="apply_raise",
        )

    def test_with_instance_vars(self) -> None:
        """Test parameterizing methods that use instance variables.

        Unlike test_simple, this tests consolidating two methods that access
        instance state. The parameterized method must correctly access the
        instance variables that both original methods needed.
        """
        self.refactor(
            "parameterize-method",
            target1="InventoryItem::mark_low_stock",
            target2="InventoryItem::mark_critical_stock",
            new_name="mark_stock_level",
        )

    def test_name_conflict(self) -> None:
        """Test parameterizing methods when the new name already exists.

        This is an edge case where the parameterized method name would
        conflict with an existing method. The refactoring must handle
        this gracefully.
        """
        self.refactor(
            "parameterize-method",
            target1="Employee::five_percent_raise",
            target2="Employee::ten_percent_raise",
            new_name="raise_salary",
        )
