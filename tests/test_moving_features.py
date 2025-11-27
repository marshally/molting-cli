"""
Tests for Moving Features refactorings.

This module tests refactorings that move functionality between classes
and create new classes.
"""

import pytest

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

    def test_with_instance_vars(self) -> None:
        """Test move method with instance variables."""
        self.refactor("move-method", source="Account::calculate_interest", to="AccountType")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test move method with decorated methods."""
        self.refactor("move-method", source="Account::balance", to="AccountType")

    def test_multiple_calls(self) -> None:
        """Test move method with multiple call sites."""
        self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test move method when target class already has method with same name."""
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("move-method", source="Account::overdraft_charge", to="AccountType")


class TestMoveField(RefactoringTestBase):
    """Tests for Move Field refactoring."""

    fixture_category = "moving_features/move_field"

    def test_simple(self) -> None:
        """Move a field to the class that uses it most."""
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test move field with multiple call sites."""
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test move field with instance variables."""
        self.refactor("move-field", source="Account::interest_rate", to="AccountType")

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test move field when target class already has field with same name."""
        with pytest.raises(ValueError, match="already has a field"):
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

    def test_with_instance_vars(self) -> None:
        """Test extract class with instance variables."""
        self.refactor(
            "extract-class",
            source="Employee",
            fields="salary,bonus_percentage,deduction_rate,tax_rate",
            methods="calculate_gross_pay,calculate_net_pay,get_annual_compensation",
            name="Compensation",
        )

    @pytest.mark.skip(reason="Implementation needed for multiple_calls")
    def test_multiple_calls(self) -> None:
        """Test extract class with multiple call sites."""
        self.refactor(
            "extract-class",
            source="Person",
            fields="office_area_code,office_number",
            methods="get_telephone_number",
            name="TelephoneNumber",
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test extract class with decorated methods."""
        self.refactor(
            "extract-class",
            source="Employee",
            fields="street,city,state,zip_code",
            methods="full_address,update_street",
            name="Address",
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test extract class when target class name already exists."""
        with pytest.raises(ValueError, match="Class .* already exists"):
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

    def test_with_instance_vars(self) -> None:
        """Test inline class with instance variables."""
        self.refactor("inline-class", source_class="Compensation", into="Employee")

    def test_with_decorators(self) -> None:
        """Test inline class with decorated methods."""
        self.refactor("inline-class", source_class="Address", into="Employee")

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test inline class when target class already has method with same name."""
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("inline-class", source_class="TelephoneNumber", into="Person")


class TestHideDelegate(RefactoringTestBase):
    """Tests for Hide Delegate refactoring."""

    fixture_category = "moving_features/hide_delegate"

    def test_simple(self) -> None:
        """Create methods on server to hide the delegate."""
        self.refactor("hide-delegate", target="Person::department")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test hide delegate with instance variables."""
        self.refactor("hide-delegate", target="Employee::compensation")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test hide delegate with decorated properties."""
        self.refactor("hide-delegate", target="Employee::compensation")

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test hide delegate when delegating method name already exists."""
        with pytest.raises(ValueError, match="already has a method"):
            self.refactor("hide-delegate", target="Person::department")


class TestRemoveMiddleMan(RefactoringTestBase):
    """Tests for Remove Middle Man refactoring."""

    fixture_category = "moving_features/remove_middle_man"

    def test_simple(self) -> None:
        """Get the client to call the delegate directly."""
        self.refactor("remove-middle-man", target="Person")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test remove middle man with instance variables."""
        self.refactor("remove-middle-man", target="Employee")


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

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test introduce foreign method with local variables."""
        self.refactor(
            "introduce-foreign-method",
            target="Report::generate#L12",
            for_class="date",
            name="add_days",
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test introduce foreign method when method name already exists."""
        with pytest.raises(ValueError, match="already has a method"):
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

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test introduce local extension with decorated methods."""
        self.refactor(
            "introduce-local-extension", target_class="list", name="EnhancedList", type="subclass"
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test introduce local extension when class name already exists."""
        with pytest.raises(ValueError, match="Class .* already exists"):
            self.refactor(
                "introduce-local-extension", target_class="date", name="MfDate", type="subclass"
            )
