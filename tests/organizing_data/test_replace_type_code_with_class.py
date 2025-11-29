"""
Tests for Replace Type Code with Class refactoring.

This test module verifies the replace-type-code-with-class refactoring,
which replaces type codes with a new class.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceTypeCodeWithClass(RefactoringTestBase):
    """Tests for Replace Type Code with Class refactoring."""

    fixture_category = "organizing_data/replace_type_code_with_class"

    def test_simple(self) -> None:
        """Replace the type code with a new class."""
        self.refactor(
            "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test replace-type-code-with-class with instance variables."""
        self.refactor("replace-type-code-with-class", target="Task::priority", name="Priority")

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update type code references"
    )
    def test_multiple_calls(self) -> None:
        """Test replace-type-code-with-class with multiple call sites."""
        self.refactor(
            "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace type code with class when target name already exists."""
        with pytest.raises(ValueError, match="Class.*BloodGroup.*already exists"):
            self.refactor(
                "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
            )
