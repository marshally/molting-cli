"""Tests for Replace Constructor with Factory Function refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceConstructorWithFactoryFunction(RefactoringTestBase):
    """Tests for Replace Constructor with Factory Function refactoring."""

    fixture_category = "simplifying_method_calls/replace_constructor_with_factory_function"

    def test_simple(self) -> None:
        """Test replacing a constructor with a factory function in the basic case.

        This is the simplest case: converting a constructor to a factory function
        (e.g., Employee.__init__() becomes create_employee()). Verifies the core
        transformation works before testing multiple call sites.
        """
        self.refactor("replace-constructor-with-factory-function", target="Employee::__init__")

    @pytest.mark.skip(reason="Implementation needed for call site updates")
    def test_multiple_calls(self) -> None:
        """Test replacing constructor with factory function across multiple call sites.

        Unlike test_simple, this verifies that all locations that instantiate the
        class are updated to call the factory function instead (e.g., Employee()
        becomes create_employee()). This is essential for the transformation to be complete.
        """
        self.refactor("replace-constructor-with-factory-function", target="Employee::__init__")

    def test_name_conflict(self) -> None:
        """Test replacing constructor when the factory function name already exists.

        This is an edge case where the proposed factory function name would
        conflict with an existing function. The refactoring must handle this
        gracefully, either by detecting it or preventing it.
        """
        self.refactor("replace-constructor-with-factory-function", target="Employee::__init__")
