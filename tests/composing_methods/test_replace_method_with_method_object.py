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
        """Turn a long method into its own object."""
        self.refactor("replace-method-with-method-object", target="Account::gamma")

    def test_with_instance_vars(self) -> None:
        """Test replace method with method object with instance variables."""
        # Convert method that uses multiple instance vars to method object
        self.refactor("replace-method-with-method-object", target="Order::calculate_total")

    def test_name_conflict(self) -> None:
        """Test replace method with method object when class name already exists."""
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard
        # Try to create Gamma class but it already exists - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            refactor_file(
                "replace-method-with-method-object", self.test_file, target="Account::gamma"
            )

    def test_with_decorators(self) -> None:
        """Test replace method with method object with decorated methods."""
        # Convert @log_call decorated method to method object
        self.refactor("replace-method-with-method-object", target="Report::generate_summary")

    def test_multiple_calls(self) -> None:
        """Test replace method with method object with multiple call sites."""
        self.refactor("replace-method-with-method-object", target="Account::gamma")
