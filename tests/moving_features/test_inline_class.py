"""
Tests for Inline Class refactoring.

This module tests the Inline Class refactoring which moves all features from one class into another.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestInlineClass(RefactoringTestBase):
    """Tests for Inline Class refactoring."""

    fixture_category = "moving_features/inline_class"

    def test_simple(self) -> None:
        """Move all features from one class into another."""
        self.refactor("inline-class", source_class="TelephoneNumber", into="Person")

    def test_with_instance_vars(self) -> None:
        """Test inline class with instance variables."""
        self.refactor("inline-class", source_class="Compensation", into="Employee")

    def test_with_decorators(self) -> None:
        """Test inline class with decorated methods."""
        self.refactor("inline-class", source_class="Address", into="Employee")

    @pytest.mark.skip(reason="Implementation needs call site update fix")
    def test_multiple_calls(self) -> None:
        """Test inline class with multiple call sites."""
        self.refactor("inline-class", source_class="TelephoneNumber", into="Person")

    def test_name_conflict(self) -> None:
        """Test inline class when target class already has method with same name."""
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("inline-class", source_class="TelephoneNumber", into="Person")
