"""Tests for Hide Method refactoring."""


from tests.conftest import RefactoringTestBase


class TestHideMethod(RefactoringTestBase):
    """Tests for Hide Method refactoring."""

    fixture_category = "simplifying_method_calls/hide_method"

    def test_simple(self) -> None:
        """Test changing a public method to private without external callers.

        This is the basic case: making a method private when it's only called
        from within its own class. Verifies the core transformation (changing
        visibility) works before testing multiple call sites or decorators.
        """
        self.refactor("hide-method", target="Employee::get_bonus_multiplier")

    def test_with_decorators(self) -> None:
        """Test hiding a decorated method.

        Unlike test_simple which has no decorators, this verifies that
        decorators (e.g., @property, @staticmethod, @classmethod) are
        preserved when changing method visibility to private.
        """
        self.refactor("hide-method", target="Calculator::calculate_discount_rate")

    def test_with_instance_vars(self) -> None:
        """Test hiding a method that uses instance variables.

        Unlike test_simple which may not use instance state, this tests hiding
        a method that accesses instance variables (e.g., self.price). Verifies
        that instance references remain valid after the visibility change.
        """
        self.refactor("hide-method", target="PriceCalculator::apply_discount")
