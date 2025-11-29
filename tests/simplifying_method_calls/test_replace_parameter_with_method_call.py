"""Tests for Replace Parameter with Method Call refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceParameterWithMethodCall(RefactoringTestBase):
    """Tests for Replace Parameter with Method Call refactoring."""

    fixture_category = "simplifying_method_calls/replace_parameter_with_method_call"

    def test_simple(self) -> None:
        """Test replacing a parameter with a method call in a simple case.

        This is the basic case: replacing a parameter (discount_level) with
        a method call that computes the value. Verifies the parameter is removed
        and the method call is inserted correctly before testing multiple call sites.
        """
        self.refactor(
            "replace-parameter-with-method-call", target="Order::discounted_price::discount_level"
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test replacing a parameter with method call across multiple call sites.

        Unlike test_simple, this tests whether all method call sites correctly
        pass the parameter (or don't when the replacement happens). This is
        important for ensuring the transformation is complete.
        """
        self.refactor(
            "replace-parameter-with-method-call", target="Order::discounted_price::discount_level"
        )

    @pytest.mark.skip(reason="Requires method call insertion with local variable scope analysis")
    def test_with_locals(self) -> None:
        """Test replacing a parameter with method call when local variables are involved.

        Unlike test_simple which may not involve local variables, this tests
        the refactoring when the method body contains local variable definitions.
        Verifies that the method call replacement works correctly in complex scopes.
        """
        self.refactor(
            "replace-parameter-with-method-call", target="ShoppingCart::apply_charges::shipping"
        )
