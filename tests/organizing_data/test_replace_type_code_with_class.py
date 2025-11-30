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
        """Test basic replacement of a type code with a new dedicated class.

        This is the simplest case: converting a primitive type code field into a proper
        class with dedicated behavior. Verifies the core transformation works before
        testing instance variables or name conflicts.
        """
        self.refactor(
            "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test type-code-to-class replacement with complex instance state.

        Unlike test_simple which uses simple type codes, this verifies that type codes
        in classes with multiple instance variables are properly replaced. Currently
        skipped due to fixture loading issues.
        """
        self.refactor("replace-type-code-with-class", target="Task::priority", name="Priority")

    def test_multiple_calls(self) -> None:
        """Test type-code-to-class replacement when type codes are used in multiple locations.

        Unlike test_simple, this verifies that all references to the type code are properly
        updated to use the new class instances. Currently skipped as the implementation
        doesn't yet update all type code references across the codebase.
        """
        self.refactor(
            "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
        )

    def test_name_conflict(self) -> None:
        """Test that type-code-to-class replacement fails when class name already exists.

        Unlike test_simple which creates a new class, this verifies proper error handling
        when the requested class name (BloodGroup) would conflict with an existing class.
        This is important to prevent accidental overwriting of existing code.
        Currently skipped as implementation needs to detect and report class name conflicts.
        """
        with pytest.raises(ValueError, match="Class.*BloodGroup.*already exists"):
            self.refactor(
                "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
            )
