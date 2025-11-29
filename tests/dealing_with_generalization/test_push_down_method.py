"""
Tests for Push Down Method refactoring.

This refactoring moves a method from a superclass to those subclasses
that specifically need it.
"""

from tests.conftest import RefactoringTestBase


class TestPushDownMethod(RefactoringTestBase):
    """Tests for Push Down Method refactoring."""

    fixture_category = "dealing_with_generalization/push_down_method"

    def test_simple(self) -> None:
        """Test basic push-down of a method from superclass to subclass.

        Moves the get_quota method from the Employee superclass to only the
        Salesman subclass where it's needed. This is the simplest case: a single
        method with no special complications, moving to one subclass. Verifies the
        core method move operation works before testing edge cases.
        """
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")

    def test_with_instance_vars(self) -> None:
        """Test push-down-method when method references instance variables.

        Unlike test_simple, this tests pushing down calculate_bonus, which may
        reference instance variables specific to Salesman or shared with the
        superclass. The refactoring must ensure all variable references remain
        valid in the subclass context.
        """
        self.refactor("push-down-method", target="Employee::calculate_bonus", to="Salesman")

    def test_name_conflict(self) -> None:
        """Test push-down-method when target subclass already has a method with the same name.

        Unlike test_simple, this tests the conflict case where Salesman already
        defines a get_quota method. The refactoring should either merge the methods
        appropriately or raise a clear error about the conflict.
        """
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")

    def test_with_decorators(self) -> None:
        """Test push-down-method with decorated methods like @classmethod.

        Unlike test_simple, this tests pushing down create_from_config which is
        decorated with @classmethod. The refactoring must preserve the decorator
        when moving the method to the subclass and maintain correct semantics.
        """
        self.refactor("push-down-method", target="Employee::create_from_config", to="Salesman")

    def test_multiple_calls(self) -> None:
        """Test push-down-method when the method is called at multiple call sites.

        Unlike test_simple, this tests that when get_quota is referenced in multiple
        locations throughout the codebase, all call sites are correctly updated to
        reference the subclass version instead of the parent class version.
        """
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")
