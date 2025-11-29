"""Tests for Remove Parameter refactoring."""


from tests.conftest import RefactoringTestBase


class TestRemoveParameter(RefactoringTestBase):
    """Tests for Remove Parameter refactoring."""

    fixture_category = "simplifying_method_calls/remove_parameter"

    def test_simple(self) -> None:
        """Test removing an unused parameter from a simple method.

        This is the basic case: removing a parameter (discount_code) that the
        method no longer needs. Verifies the parameter is removed from the
        method signature before testing multiple call sites or decorators.
        """
        self.refactor("remove-parameter", target="Order::calculate_total::discount_code")

    def test_with_decorators(self) -> None:
        """Test removing a parameter from a method with decorators.

        Unlike test_simple which has no decorators, this verifies that
        decorators (e.g., @property, @staticmethod) are preserved when
        removing a parameter from the method signature.
        """
        self.refactor("remove-parameter", target="ReportGenerator::generate_report::unused_param")

    def test_multiple_calls(self) -> None:
        """Test removing a parameter when the method is called from multiple locations.

        Unlike test_simple, this verifies that all call sites are updated to remove
        the parameter from their method calls. Missing even one call site would break
        the code, making this test critical for completeness.
        """
        self.refactor("remove-parameter", target="Order::calculate_total::discount_code")

    def test_with_instance_vars(self) -> None:
        """Test removing a parameter from a method that uses instance variables.

        Unlike test_simple which may be from a simple class, this tests removing
        a parameter from a method that accesses instance state. Verifies that
        instance variable references remain valid after parameter removal.
        """
        self.refactor("remove-parameter", target="EmailService::send_email::priority")
