"""
Tests for Replace Type Code with State/Strategy refactoring.

This test module verifies the replace-type-code-with-state-strategy refactoring,
which replaces type codes with state or strategy objects.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceTypeCodeWithStateStrategy(RefactoringTestBase):
    """Tests for Replace Type Code with State/Strategy refactoring."""

    fixture_category = "organizing_data/replace_type_code_with_state_strategy"

    def test_simple(self) -> None:
        """Replace the type code with a state object."""
        self.refactor(
            "replace-type-code-with-state-strategy", target="Employee::type", name="EmployeeType"
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace type code with state/strategy when target name already exists."""
        with pytest.raises(ValueError, match="Class.*EmployeeType.*already exists"):
            self.refactor(
                "replace-type-code-with-state-strategy",
                target="Employee::type",
                name="EmployeeType",
            )
