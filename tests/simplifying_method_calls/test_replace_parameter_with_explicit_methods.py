"""Tests for Replace Parameter with Explicit Methods refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceParameterWithExplicitMethods(RefactoringTestBase):
    """Tests for Replace Parameter with Explicit Methods refactoring."""

    fixture_category = "simplifying_method_calls/replace_parameter_with_explicit_methods"

    def test_simple(self) -> None:
        """Create a separate method for each value of the parameter."""
        self.refactor("replace-parameter-with-explicit-methods", target="Employee::set_value::name")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test replace parameter with explicit methods with decorated methods."""
        self.refactor(
            "replace-parameter-with-explicit-methods", target="Configuration::set_value::name"
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test replace parameter with explicit methods with multiple call sites."""
        self.refactor("replace-parameter-with-explicit-methods", target="Employee::set_value::name")

    def test_name_conflict(self) -> None:
        """Test replace parameter with explicit methods when target name already exists."""
        self.refactor("replace-parameter-with-explicit-methods", target="Employee::set_value::name")
