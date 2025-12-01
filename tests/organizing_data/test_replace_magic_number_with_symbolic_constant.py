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
        """Test basic replacement of a magic number with a symbolic constant.

        This is the simplest case: creating a named constant and replacing a magic number
        with it to improve code readability. Verifies the core transformation works before
        testing cases with local variables or name conflicts.
        """
        self.refactor(
            "replace-magic-number-with-symbolic-constant",
            target="potential_energy#L2",
            name="GRAVITATIONAL_CONSTANT",
        )

    def test_with_locals(self) -> None:
        """Test magic number replacement when same magic number appears in multiple functions.

        Unlike test_simple which replaces a single occurrence, this verifies that all
        occurrences of the same magic number value are replaced consistently. Currently skipped
        as the implementation only replaces in the targeted function, not all matching occurrences.
        """
        self.refactor(
            "replace-magic-number-with-symbolic-constant",
            target="potential_energy#L5",
            name="GRAVITATIONAL_CONSTANT",
        )

    def test_name_conflict(self) -> None:
        """Test that magic number replacement fails when the constant name already exists.

        Unlike test_simple which creates a new constant, this verifies proper error handling
        when the requested constant name (GRAVITATIONAL_CONSTANT) would conflict with an
        existing constant. Prevents accidental overwriting of existing constants.
        Currently skipped as implementation needs to detect and report name conflicts.
        """
        with pytest.raises(ValueError, match="Constant.*GRAVITATIONAL_CONSTANT.*already exists"):
            self.refactor(
                "replace-magic-number-with-symbolic-constant",
                target="potential_energy#L2",
                name="GRAVITATIONAL_CONSTANT",
            )
