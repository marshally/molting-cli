"""Tests for Replace Parameter with Method Call refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceParameterWithMethodCall(RefactoringTestBase):
    """Tests for Replace Parameter with Method Call refactoring."""

    fixture_category = "simplifying_method_calls/replace_parameter_with_method_call"

    def test_simple(self) -> None:
        """Remove the parameter and have the receiver call the method."""
        self.refactor(
            "replace-parameter-with-method-call", target="Order::discounted_price::discount_level"
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test replace parameter with method call with multiple call sites."""
        self.refactor(
            "replace-parameter-with-method-call", target="Order::discounted_price::discount_level"
        )

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test replace parameter with method call with local variables."""
        self.refactor(
            "replace-parameter-with-method-call", target="ShoppingCart::apply_charges::shipping"
        )
