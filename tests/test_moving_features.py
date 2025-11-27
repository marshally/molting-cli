"""
Tests for Moving Features refactorings.

This module tests refactorings that move functionality between classes
and create new classes.
"""

from tests.conftest import RefactoringTestBase


class TestMoveMethod(RefactoringTestBase):
    """Tests for Move Method refactoring."""

    fixture_category = "moving_features/move_method"

    def test_simple(self) -> None:
        """Move a method to the class that uses it most."""
        self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")

    def test_with_locals(self) -> None:
        """Test move method with local variables."""
        self.refactor("move-method", source="Account::calculate_fees", to="AccountType")


class TestMoveField(RefactoringTestBase):
    """Tests for Move Field refactoring."""

    fixture_category = "moving_features/move_field"

    def test_simple(self) -> None:
        """Move a field to the class that uses it most."""
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")


class TestExtractClass(RefactoringTestBase):
    """Tests for Extract Class refactoring."""

    fixture_category = "moving_features/extract_class"

    def test_simple(self) -> None:
        """Create a new class and move relevant fields and methods."""
        self.refactor(
            "extract-class",
            source="Person",
            fields="office_area_code,office_number",
            methods="get_telephone_number",
            name="TelephoneNumber",
        )


class TestInlineClass(RefactoringTestBase):
    """Tests for Inline Class refactoring."""

    fixture_category = "moving_features/inline_class"

    def test_simple(self) -> None:
        """Move all features from one class into another."""
        self.refactor("inline-class", source_class="TelephoneNumber", into="Person")


class TestHideDelegate(RefactoringTestBase):
    """Tests for Hide Delegate refactoring."""

    fixture_category = "moving_features/hide_delegate"

    def test_simple(self) -> None:
        """Create methods on server to hide the delegate."""
        self.refactor("hide-delegate", target="Person::department")


class TestRemoveMiddleMan(RefactoringTestBase):
    """Tests for Remove Middle Man refactoring."""

    fixture_category = "moving_features/remove_middle_man"

    def test_simple(self) -> None:
        """Get the client to call the delegate directly."""
        self.refactor("remove-middle-man", target="Person")


class TestIntroduceForeignMethod(RefactoringTestBase):
    """Tests for Introduce Foreign Method refactoring."""

    fixture_category = "moving_features/introduce_foreign_method"

    def test_simple(self) -> None:
        """Create method in client with server instance as first arg."""
        self.refactor(
            "introduce-foreign-method",
            target="Report::generate#L6",
            for_class="date",
            name="next_day",
        )


class TestIntroduceLocalExtension(RefactoringTestBase):
    """Tests for Introduce Local Extension refactoring."""

    fixture_category = "moving_features/introduce_local_extension"

    def test_simple(self) -> None:
        """Create new class with extra methods as subclass/wrapper."""
        self.refactor(
            "introduce-local-extension", target_class="date", name="MfDate", type="subclass"
        )
