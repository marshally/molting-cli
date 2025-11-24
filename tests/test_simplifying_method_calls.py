"""
Tests for Simplifying Method Calls refactorings.

This module tests refactorings that improve method interfaces by simplifying
how they are called, removing unnecessary parameters, and improving readability.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestRenameMethod(RefactoringTestBase):
    """Tests for Rename Method refactoring."""

    fixture_category = "simplifying_method_calls/rename_method"

    def test_simple(self) -> None:
        """Rename a method to better reveal its purpose."""
        self.refactor(
            "rename-method", target="Customer::get_inv_cdtlmt", new_name="get_invoice_credit_limit"
        )


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


class TestRemoveParameter(RefactoringTestBase):
    """Tests for Remove Parameter refactoring."""

    fixture_category = "simplifying_method_calls/remove_parameter"

    def test_simple(self) -> None:
        """Remove a parameter that is no longer used."""
        self.refactor("remove-parameter", target="Order::calculate_total::discount_code")


@pytest.mark.skip(reason="No implementation yet")
class TestSeparateQueryFromModifier(RefactoringTestBase):
    """Tests for Separate Query from Modifier refactoring."""

    fixture_category = "simplifying_method_calls/separate_query_from_modifier"

    def test_simple(self) -> None:
        """Create two methods, one for the query and one for the modification."""
        self.refactor("separate-query-from-modifier", target="Security::get_and_remove_intruder")


class TestParameterizeMethod(RefactoringTestBase):
    """Tests for Parameterize Method refactoring."""

    fixture_category = "simplifying_method_calls/parameterize_method"

    def test_simple(self) -> None:
        """Create one method that uses a parameter for different values."""
        self.refactor(
            "parameterize-method",
            target1="Employee::five_percent_raise",
            target2="Employee::ten_percent_raise",
            new_name="raise_salary",
        )


@pytest.mark.skip(reason="No implementation yet")
class TestReplaceParameterWithExplicitMethods(RefactoringTestBase):
    """Tests for Replace Parameter with Explicit Methods refactoring."""

    fixture_category = "simplifying_method_calls/replace_parameter_with_explicit_methods"

    def test_simple(self) -> None:
        """Create a separate method for each value of the parameter."""
        self.refactor("replace-parameter-with-explicit-methods", target="Employee::set_value::name")


@pytest.mark.skip(reason="No implementation yet")
class TestPreserveWholeObject(RefactoringTestBase):
    """Tests for Preserve Whole Object refactoring."""

    fixture_category = "simplifying_method_calls/preserve_whole_object"

    def test_simple(self) -> None:
        """Send the whole object instead of extracting values from it."""
        self.refactor("preserve-whole-object", target="within_plan")


@pytest.mark.skip(reason="No implementation yet")
class TestReplaceParameterWithMethodCall(RefactoringTestBase):
    """Tests for Replace Parameter with Method Call refactoring."""

    fixture_category = "simplifying_method_calls/replace_parameter_with_method_call"

    def test_simple(self) -> None:
        """Remove the parameter and have the receiver call the method."""
        self.refactor(
            "replace-parameter-with-method-call", target="Order::discounted_price::discount_level"
        )


@pytest.mark.skip(reason="No implementation yet")
class TestIntroduceParameterObject(RefactoringTestBase):
    """Tests for Introduce Parameter Object refactoring."""

    fixture_category = "simplifying_method_calls/introduce_parameter_object"

    def test_simple(self) -> None:
        """Replace parameters with a parameter object."""
        self.refactor(
            "introduce-parameter-object",
            target="flow_between",
            params="start_date,end_date",
            name="DateRange",
        )


class TestRemoveSettingMethod(RefactoringTestBase):
    """Tests for Remove Setting Method refactoring."""

    fixture_category = "simplifying_method_calls/remove_setting_method"

    def test_simple(self) -> None:
        """Make the field immutable by removing the setter."""
        self.refactor("remove-setting-method", target="Account::_id")


class TestHideMethod(RefactoringTestBase):
    """Tests for Hide Method refactoring."""

    fixture_category = "simplifying_method_calls/hide_method"

    def test_simple(self) -> None:
        """Make the method private."""
        self.refactor("hide-method", target="Employee::get_bonus_multiplier")


class TestReplaceConstructorWithFactoryFunction(RefactoringTestBase):
    """Tests for Replace Constructor with Factory Function refactoring."""

    fixture_category = "simplifying_method_calls/replace_constructor_with_factory_function"

    def test_simple(self) -> None:
        """Replace the constructor with a factory function."""
        self.refactor("replace-constructor-with-factory-function", target="Employee::__init__")


class TestReplaceErrorCodeWithException(RefactoringTestBase):
    """Tests for Replace Error Code with Exception refactoring."""

    fixture_category = "simplifying_method_calls/replace_error_code_with_exception"

    def test_simple(self) -> None:
        """Throw an exception instead of returning an error code."""
        self.refactor("replace-error-code-with-exception", target="withdraw")


@pytest.mark.skip(reason="No implementation yet")
class TestReplaceExceptionWithTest(RefactoringTestBase):
    """Tests for Replace Exception with Test refactoring."""

    fixture_category = "simplifying_method_calls/replace_exception_with_test"

    def test_simple(self) -> None:
        """Change the caller to test first instead of catching exception."""
        self.refactor("replace-exception-with-test", target="get_value_for_period")
