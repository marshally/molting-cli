"""Tests for Introduce Explaining Variable refactoring.

Tests for the Introduce Explaining Variable refactoring, which puts
complex expressions into named temp variables for clarity.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceExplainingVariable(RefactoringTestBase):
    """Tests for Introduce Explaining Variable refactoring."""

    fixture_category = "composing_methods/introduce_explaining_variable"

    def test_simple(self) -> None:
        """Test basic introduce explaining variable using line number targeting.

        This test applies the refactoring multiple times using line number targeting
        (#L3, #L5, #L7). It verifies that complex expressions are extracted into
        named temporary variables with descriptive names. This is the foundational
        case using explicit line targeting, which requires tracking line shifts
        as new variables are introduced.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard

        # Apply all three refactorings before checking
        # Note: Line numbers shift as variables are introduced
        # Original: L3=base_price expr, L4=quantity_discount expr, L5=shipping expr
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L3",
            name="base_price",
        )
        # After first: L5=quantity_discount expr (shifted due to new assignment)
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L5",
            name="quantity_discount",
        )
        # After second: L7=shipping expr (min(...) is on line 7)
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L7",
            name="shipping",
        )
        self.assert_matches_expected()

    def test_name_conflict(self) -> None:
        """Test that name conflict is detected when the variable name already exists.

        This test verifies error handling: when extracting a complex expression
        into a named variable, if that variable name (e.g., base_price) already
        exists in the function scope, the refactoring should raise a ValueError
        instead of creating a shadowing variable or silently overwriting.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard
        # Try to introduce base_price but it already exists - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            refactor_file(
                "introduce-explaining-variable",
                self.test_file,
                target="calculate_total#L7",
                name="base_price",
            )


class TestIntroduceExplainingVariableReplaceAll(RefactoringTestBase):
    """Tests for Introduce Explaining Variable with replace_all option."""

    fixture_category = "composing_methods/introduce_explaining_variable/replace_all"

    def test_simple(self) -> None:
        """Extract expression and replace all occurrences with the variable.

        This tests the more advanced version of introduce-explaining-variable
        that also replaces other occurrences of the extracted expression with
        the new variable name. For example, extracting `order.quantity * order.item_price`
        to `base_price` should also replace `order.quantity * order.item_price` in
        the min() call with `base_price`.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard

        # Apply refactorings with replace_all=True
        # Note: Line numbers shift as variables are introduced
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L3",
            name="base_price",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L5",
            name="quantity_discount",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L7",
            name="shipping",
            replace_all=True,
        )
        self.assert_matches_expected()

    def test_condensed(self) -> None:
        """Extract expressions using expression-based targeting (not line numbers).

        This tests the expression-based targeting mode using --in_function and
        --expression parameters. This is useful when expressions span multiple
        lines or don't have clean line boundaries.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard

        # Use expression-based targeting - no need to track line numbers!
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            in_function="calculate_total",
            expression="order.quantity * order.item_price",
            name="base_price",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            in_function="calculate_total",
            expression="max(0, order.quantity - 500) * order.item_price * 0.05",
            name="quantity_discount",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            in_function="calculate_total",
            expression="min(base_price * 0.1, 100.0)",
            name="shipping",
            replace_all=True,
        )
        self.assert_matches_expected()
