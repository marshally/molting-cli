"""Tests for Parameterize Method refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestParameterizeMethod(RefactoringTestBase):
    """Tests for Parameterize Method refactoring."""

    fixture_category = "simplifying_method_calls/parameterize_method"

    def test_simple(self) -> None:
        """Create one method that uses a parameter for different values."""
        self.refactor(
            "parameterize-method",
            target1="Employee::five_percent_raise",
            target2="Employee::ten_percent_raise",
            new_name="raise_salary",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test parameterize method with decorated methods."""
        self.refactor(
            "parameterize-method",
            target1="Employee::small_raise",
            target2="Employee::large_raise",
            new_name="apply_raise",
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test parameterize method with instance variables."""
        self.refactor(
            "parameterize-method",
            target1="InventoryItem::mark_low_stock",
            target2="InventoryItem::mark_critical_stock",
            new_name="mark_stock_level",
        )

    def test_name_conflict(self) -> None:
        """Test parameterize method when target name already exists."""
        self.refactor(
            "parameterize-method",
            target1="Employee::five_percent_raise",
            target2="Employee::ten_percent_raise",
            new_name="raise_salary",
        )
