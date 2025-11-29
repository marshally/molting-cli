"""Tests for Replace Constructor with Factory Function refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceConstructorWithFactoryFunction(RefactoringTestBase):
    """Tests for Replace Constructor with Factory Function refactoring."""

    fixture_category = "simplifying_method_calls/replace_constructor_with_factory_function"

    def test_simple(self) -> None:
        """Replace the constructor with a factory function."""
        self.refactor("replace-constructor-with-factory-function", target="Employee::__init__")

    @pytest.mark.skip(reason="Implementation needed for call site updates")
    def test_multiple_calls(self) -> None:
        """Test replace constructor with factory function with multiple call sites."""
        self.refactor("replace-constructor-with-factory-function", target="Employee::__init__")

    def test_name_conflict(self) -> None:
        """Test replace constructor with factory function when factory name already exists."""
        self.refactor("replace-constructor-with-factory-function", target="Employee::__init__")
