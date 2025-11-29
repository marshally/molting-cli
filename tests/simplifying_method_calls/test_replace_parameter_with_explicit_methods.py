"""Tests for Replace Parameter with Explicit Methods refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceParameterWithExplicitMethods(RefactoringTestBase):
    """Tests for Replace Parameter with Explicit Methods refactoring."""

    fixture_category = "simplifying_method_calls/replace_parameter_with_explicit_methods"

    def test_simple(self) -> None:
        """Test replacing a parameter with explicit methods in a basic case.

        This is the simplest case: replacing a parameter (e.g., set_value(name, value))
        with separate explicit methods (set_name(), set_age()). Verifies the core
        transformation works before testing multiple call sites or decorators.
        """
        self.refactor("replace-parameter-with-explicit-methods", target="Employee::set_value::name")

    def test_with_decorators(self) -> None:
        """Test replacing a parameter with explicit methods on decorated methods.

        Unlike test_simple, this tests when the original method has decorators.
        The refactoring must preserve decorators while creating explicit methods.
        """
        self.refactor(
            "replace-parameter-with-explicit-methods", target="Configuration::set_value::name"
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test replacing a parameter with explicit methods across multiple call sites.

        Unlike test_simple, this verifies that all call sites calling set_value()
        are updated to call the appropriate explicit method (set_name(), set_age()).
        Missing one call site would break the code.
        """
        self.refactor("replace-parameter-with-explicit-methods", target="Employee::set_value::name")

    def test_name_conflict(self) -> None:
        """Test replacing a parameter when a proposed explicit method name already exists.

        This is an edge case where one of the explicit methods being created
        (e.g., set_name()) would conflict with an existing method. The refactoring
        must handle this gracefully.
        """
        self.refactor("replace-parameter-with-explicit-methods", target="Employee::set_value::name")
