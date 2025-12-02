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
        """Test inlining a class by moving all its features into another class.

        This baseline case moves all fields and methods from a simple extracted class
        back into the target class. Verifies basic inlining works and that the source
        class can be safely removed after the transformation.
        """
        self.refactor("inline-class", source_class="TelephoneNumber", into="Person")

    def test_with_instance_vars(self) -> None:
        """Test inlining a class whose methods access multiple instance variables.

        Unlike test_simple, this tests inlining classes with complex state where
        multiple fields interact. Verifies that intra-class field references are
        correctly handled when merging the classes together.
        """
        self.refactor("inline-class", source_class="Compensation", into="Employee")

    def test_with_decorators(self) -> None:
        """Test inlining a class that contains decorated methods.

        When inlining a class with decorators (e.g., @property methods), the
        decorators must be preserved on the inlined methods in the target class.
        Tests proper handling of method metadata during inlining.
        """
        self.refactor("inline-class", source_class="Address", into="Employee")

    def test_multiple_calls(self) -> None:
        """Test inlining a class when its instances are created and used in multiple places.

        When a class is instantiated and used from various call sites throughout
        the codebase, inlining must update all those locations to use the target
        class instead. Tests comprehensive call site transformation.
        """
        self.refactor("inline-class", source_class="TelephoneNumber", into="Person")

    def test_name_conflict(self) -> None:
        """Test that inline class raises error when method names conflict.

        This error handling test verifies the refactoring detects when inlining
        would create a naming conflict in the target class. Prevents silent method
        overwrites that could lose functionality.
        """
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("inline-class", source_class="TelephoneNumber", into="Person")

    @pytest.mark.skip(reason="Multi-file refactoring not yet implemented")
    def test_multi_file(self) -> None:
        """Test inline-class when references span multiple files.

        Inlines PhoneNumber into Person and updates all call sites
        in directory.py from person.phone_number.area_code to person.area_code.
        """
        self.refactor_directory(
            "inline-class", target="person.py", source_class="PhoneNumber", into="Person"
        )
