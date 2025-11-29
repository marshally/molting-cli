"""Tests for Add Parameter refactoring."""


from tests.conftest import RefactoringTestBase


class TestAddParameter(RefactoringTestBase):
    """Tests for Add Parameter refactoring."""

    fixture_category = "simplifying_method_calls/add_parameter"

    def test_simple(self) -> None:
        """Add a parameter for information needed by the method."""
        self.refactor(
            "add-parameter",
            target="Contact::get_contact_info",
            name="include_email",
            default="False",
        )

    def test_with_decorators(self) -> None:
        """Test add parameter with decorated methods."""
        self.refactor(
            "add-parameter",
            target="DataFormatter::format_value",
            name="uppercase",
            default="False",
        )

    def test_multiple_calls(self) -> None:
        """Test add parameter with multiple call sites."""
        self.refactor(
            "add-parameter",
            target="Contact::get_contact_info",
            name="include_email",
            default="False",
        )

    def test_with_instance_vars(self) -> None:
        """Test add parameter with instance variables."""
        self.refactor(
            "add-parameter",
            target="BankAccount::get_account_summary",
            name="include_overdraft",
            default="False",
        )
