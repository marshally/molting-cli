"""Tests for Replace Method with Method Object refactoring.

Tests for the Replace Method with Method Object refactoring, which
turns a long method into its own object.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestReplaceMethodWithMethodObject(RefactoringTestBase):
    """Tests for Replace Method with Method Object refactoring."""

    fixture_category = "composing_methods/replace_method_with_method_object"

    def test_simple(self) -> None:
        """Test basic replace method with method object refactoring.

        This is the simplest case: converting a straightforward method that has
        no dependencies on instance variables into a method object. Verifies that
        the core transformation works before testing more complex scenarios with
        instance variables and name conflicts.
        """
        self.refactor("replace-method-with-method-object", target="Account::gamma")

    def test_with_instance_vars(self) -> None:
        """Test replace method with method object that uses instance variables.

        Unlike test_simple, this case involves a method that depends on multiple
        instance variables. The refactoring must correctly pass these instance
        variables to the new method object's constructor, ensuring the extracted
        logic can still access all necessary instance state.
        """
        # Convert method that uses multiple instance vars to method object
        self.refactor("replace-method-with-method-object", target="Order::calculate_total")

    def test_name_conflict(self) -> None:
        """Test that name conflict is detected when method object class already exists.

        This test verifies error handling: when the refactoring would create a
        new class (e.g., Gamma) to hold the method object, but a class with that
        name already exists, the refactoring should raise a ValueError instead of
        silently overwriting or creating duplicate code.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard
        # Try to create Gamma class but it already exists - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            refactor_file(
                "replace-method-with-method-object", self.test_file, target="Account::gamma"
            )

    def test_with_decorators(self) -> None:
        """Test replace method with method object when the method has decorators.

        This case verifies that decorators (e.g., @log_call) on the original
        method are handled correctly during the refactoring. The decorators
        should either be preserved on the execute() method or handled appropriately
        in the extracted method object class.
        """
        # Convert @log_call decorated method to method object
        self.refactor("replace-method-with-method-object", target="Report::generate_summary")

    def test_multiple_calls(self) -> None:
        """Test replace method with method object when method is called from multiple places.

        This case ensures that when a method has multiple call sites throughout
        the codebase, the refactoring correctly replaces all callers with
        instantiation and execution of the method object, maintaining consistent
        behavior across all invocation points.
        """
        self.refactor("replace-method-with-method-object", target="Account::gamma")
