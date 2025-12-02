"""Tests for Add Parameter refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestAddParameter(RefactoringTestBase):
    """Tests for Add Parameter refactoring."""

    fixture_category = "simplifying_method_calls/add_parameter"

    def test_simple(self) -> None:
        """Test adding a parameter to a simple method with a single call site.

        This is the basic case: adding a parameter (include_email) with a default
        value to a method. Verifies that the method signature is updated and the
        default value is applied before testing multiple call sites or decorators.
        """
        self.refactor(
            "add-parameter",
            target="Contact::get_contact_info",
            name="include_email",
            default="False",
        )

    def test_with_decorators(self) -> None:
        """Test adding a parameter to a method with decorators.

        Unlike test_simple which has no decorators, this verifies that
        decorators (e.g., @staticmethod, @classmethod) are preserved when
        adding a parameter to the method signature.
        """
        self.refactor(
            "add-parameter",
            target="DataFormatter::format_value",
            name="uppercase",
            default="False",
        )

    def test_multiple_calls(self) -> None:
        """Test adding a parameter when the method is called from multiple locations.

        Unlike test_simple, this verifies that all call sites either explicitly
        pass a value for the new parameter or rely on the default value. This ensures
        the transformation is complete and doesn't break any callers.
        """
        self.refactor(
            "add-parameter",
            target="Contact::get_contact_info",
            name="include_email",
            default="False",
        )

    def test_with_instance_vars(self) -> None:
        """Test adding a parameter to a method that uses instance variables.

        Unlike test_simple which may be from a simple class, this tests adding
        a parameter to a method that accesses instance state (e.g., self.balance
        in BankAccount). Verifies that the new parameter integrates correctly
        with existing instance variable references.
        """
        self.refactor(
            "add-parameter",
            target="BankAccount::get_account_summary",
            name="include_overdraft",
            default="False",
        )

    @pytest.mark.skip(reason="Multi-file refactoring not yet implemented")
    def test_multi_file(self) -> None:
        """Test add-parameter when call sites span multiple files."""
        self.refactor_directory(
            "add-parameter",
            target="Calculator::calculate",
            name="precision",
            default="2",
        )
