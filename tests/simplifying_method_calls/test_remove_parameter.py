"""Tests for Remove Parameter refactoring."""


from tests.conftest import RefactoringTestBase


class TestRemoveParameter(RefactoringTestBase):
    """Tests for Remove Parameter refactoring."""

    fixture_category = "simplifying_method_calls/remove_parameter"

    def test_simple(self) -> None:
        """Remove a parameter that is no longer used."""
        self.refactor("remove-parameter", target="Order::calculate_total::discount_code")

    def test_with_decorators(self) -> None:
        """Test remove parameter with decorated methods."""
        self.refactor("remove-parameter", target="ReportGenerator::generate_report::unused_param")

    def test_multiple_calls(self) -> None:
        """Test remove parameter with multiple call sites."""
        self.refactor("remove-parameter", target="Order::calculate_total::discount_code")

    def test_with_instance_vars(self) -> None:
        """Test remove parameter with instance variables."""
        self.refactor("remove-parameter", target="EmailService::send_email::priority")
