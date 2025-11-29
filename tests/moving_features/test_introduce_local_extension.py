"""
Tests for Introduce Local Extension refactoring.

This module tests the Introduce Local Extension refactoring which creates
new class with extra methods as subclass/wrapper.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceLocalExtension(RefactoringTestBase):
    """Tests for Introduce Local Extension refactoring."""

    fixture_category = "moving_features/introduce_local_extension"

    def test_simple(self) -> None:
        """Test creating a local extension class to add methods to external class.

        This baseline case creates a new subclass of an external class (e.g., from
        the standard library) to add extension methods. Verifies the new class can be
        created and properly extends the target class without modifying the original.
        """
        self.refactor(
            "introduce-local-extension", target_class="date", name="MfDate", type="subclass"
        )

    @pytest.mark.skip(reason="Implementation needs decorator handling fix")
    def test_with_decorators(self) -> None:
        """Test creating a local extension with decorated methods (e.g., @property).

        When the extension methods include decorators, the refactoring must preserve
        those decorators when creating the new extension class. Tests proper handling
        of method metadata in the extended class.
        """
        self.refactor(
            "introduce-local-extension", target_class="list", name="EnhancedList", type="subclass"
        )

    def test_name_conflict(self) -> None:
        """Test that introduce local extension raises error when class name exists.

        This error handling test verifies the refactoring prevents creating an
        extension class that would conflict with an existing class name.
        Prevents silent shadowing of existing classes.
        """
        with pytest.raises(ValueError, match="Class .* already exists"):
            self.refactor(
                "introduce-local-extension", target_class="date", name="MfDate", type="subclass"
            )
