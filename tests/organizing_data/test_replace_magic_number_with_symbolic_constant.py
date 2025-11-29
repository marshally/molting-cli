"""
Tests for Replace Magic Number with Symbolic Constant refactoring.

This test module verifies the replace-magic-number-with-symbolic-constant refactoring,
which replaces magic numbers with named symbolic constants.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceMagicNumberWithSymbolicConstant(RefactoringTestBase):
    """Tests for Replace Magic Number with Symbolic Constant refactoring."""

    fixture_category = "organizing_data/replace_magic_number_with_symbolic_constant"

    def test_simple(self) -> None:
        """Create a constant, name it after the meaning, and replace the number with it."""
        self.refactor(
            "replace-magic-number-with-symbolic-constant",
            target="potential_energy#L2",
            name="GRAVITATIONAL_CONSTANT",
        )

    @pytest.mark.skip(
        reason=(
            "Implementation needed for with_locals - only replaces in targeted function, "
            "not all occurrences"
        )
    )
    def test_with_locals(self) -> None:
        """Test replace magic number with symbolic constant with local variables."""
        self.refactor(
            "replace-magic-number-with-symbolic-constant",
            target="potential_energy#L5",
            name="GRAVITATIONAL_CONSTANT",
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing constant"
    )
    def test_name_conflict(self) -> None:
        """Test replace magic number with symbolic constant when target name already exists."""
        with pytest.raises(ValueError, match="Constant.*GRAVITATIONAL_CONSTANT.*already exists"):
            self.refactor(
                "replace-magic-number-with-symbolic-constant",
                target="potential_energy#L2",
                name="GRAVITATIONAL_CONSTANT",
            )
