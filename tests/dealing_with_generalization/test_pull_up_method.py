"""
Tests for Pull Up Method refactoring.

This refactoring moves a method from subclasses to their superclass,
consolidating common behavior in the class hierarchy.
"""

from tests.conftest import RefactoringTestBase


class TestPullUpMethod(RefactoringTestBase):
    """Tests for Pull Up Method refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_method"

    def test_simple(self) -> None:
        """Test basic pull-up of an identical method from subclass to superclass.

        Moves the get_annual_cost method from Salesman to the Employee superclass.
        This is the simplest case: a single identical method being pulled up with
        no special complications. Verifies the core method consolidation works
        before testing edge cases like decorators or name conflicts.
        """
        self.refactor("pull-up-method", target="Salesman::get_annual_cost", to="Employee")

    def test_with_instance_vars(self) -> None:
        """Test pull-up-method when method references instance variables.

        Unlike test_simple, this tests pulling up get_employee_info which may
        reference instance variables from the subclass. The refactoring must
        ensure that all variable references are properly scoped and accessible
        from the superclass context.
        """
        self.refactor("pull-up-method", target="Salesman::get_employee_info", to="Employee")

    def test_name_conflict(self) -> None:
        """Test pull-up-method when target method already exists in the parent class.

        Unlike test_simple, this tests the conflict case where Employee already
        has a get_annual_cost method. The refactoring should either merge the
        implementations appropriately or raise a clear error about the conflict.
        """
        self.refactor("pull-up-method", target="Salesman::get_annual_cost", to="Employee")

    def test_with_decorators(self) -> None:
        """Test pull-up-method with decorated methods like @staticmethod.

        Unlike test_simple, this tests pulling up format_currency which is decorated
        with @staticmethod. The refactoring must preserve the decorator when moving
        the method to the superclass and maintain the correct method type semantics.
        """
        self.refactor("pull-up-method", target="Salesman::format_currency", to="Employee")

    def test_multiple_calls(self) -> None:
        """Test pull-up-method when the method is called at multiple call sites.

        Unlike test_simple, this tests that when get_annual_cost is referenced
        in multiple locations throughout the codebase, all call sites continue to
        work correctly after the method is moved to the superclass.
        """
        self.refactor("pull-up-method", target="Salesman::get_annual_cost", to="Employee")
