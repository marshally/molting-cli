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
        """Test basic replacement of a type code with a state/strategy object.

        This is the simplest case: converting a primitive type code field into a proper
        state or strategy object with dedicated behavior. Verifies the core transformation
        works before testing cases where the target class name already exists.
        """
        self.refactor(
            "replace-type-code-with-state-strategy", target="Employee::type", name="EmployeeType"
        )

    def test_name_conflict(self) -> None:
        """Test that replacing type code fails when the target state class name already exists.

        Unlike test_simple which creates a new class, this verifies proper error handling
        when the requested class name (EmployeeType) would conflict with an existing class.
        This is important to prevent accidental overwriting of existing code.
        Currently skipped as implementation needs to detect and report class name conflicts.
        """
        with pytest.raises(ValueError, match="Class.*EmployeeType.*already exists"):
            self.refactor(
                "replace-type-code-with-state-strategy",
                target="Employee::type",
                name="EmployeeType",
            )
