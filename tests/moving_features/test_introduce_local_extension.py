"""
Tests for Introduce Local Extension refactoring.

This module tests the Introduce Local Extension refactoring which creates new class with extra methods as subclass/wrapper.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceLocalExtension(RefactoringTestBase):
    """Tests for Introduce Local Extension refactoring."""

    fixture_category = "moving_features/introduce_local_extension"

    def test_simple(self) -> None:
        """Create new class with extra methods as subclass/wrapper."""
        self.refactor(
            "introduce-local-extension", target_class="date", name="MfDate", type="subclass"
        )

    @pytest.mark.skip(reason="Implementation needs decorator handling fix")
    def test_with_decorators(self) -> None:
        """Test introduce local extension with decorated methods."""
        self.refactor(
            "introduce-local-extension", target_class="list", name="EnhancedList", type="subclass"
        )

    def test_name_conflict(self) -> None:
        """Test introduce local extension when class name already exists."""
        with pytest.raises(ValueError, match="Class .* already exists"):
            self.refactor(
                "introduce-local-extension", target_class="date", name="MfDate", type="subclass"
            )
