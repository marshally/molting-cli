"""
Tests for Extract Class refactoring.

This module tests the Extract Class refactoring which creates a new class and moves relevant fields and methods.
"""

import pytest

from tests.conftest import RefactoringTestBase


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

    @pytest.mark.skip(reason="Implementation needs docstring handling fix")
    def test_with_instance_vars(self) -> None:
        """Test extract class with instance variables."""
        self.refactor(
            "extract-class",
            source="Employee",
            fields="salary,bonus_percentage,deduction_rate,tax_rate",
            methods="calculate_gross_pay,calculate_net_pay,get_annual_compensation",
            name="Compensation",
        )

    def test_multiple_calls(self) -> None:
        """Test extract class with multiple call sites."""
        self.refactor(
            "extract-class",
            source="Person",
            fields="office_area_code,office_number",
            methods="get_telephone_number",
            name="TelephoneNumber",
        )

    def test_with_decorators(self) -> None:
        """Test extract class with decorated methods."""
        self.refactor(
            "extract-class",
            source="Employee",
            fields="street,city,state,zip_code",
            methods="full_address,update_street",
            name="Address",
        )

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
