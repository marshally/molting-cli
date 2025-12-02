"""
Tests for Extract Class refactoring.

This module tests the Extract Class refactoring which creates a new class
and moves relevant fields and methods.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestExtractClass(RefactoringTestBase):
    """Tests for Extract Class refactoring."""

    fixture_category = "moving_features/extract_class"

    def test_simple(self) -> None:
        """Test extracting related fields and methods into a new class.

        This baseline case creates a new class with straightforward fields and
        methods that have no complex dependencies on the source class. Verifies
        basic extraction, new class creation, and simple method relocation work.
        """
        self.refactor(
            "extract-class",
            source="Person",
            fields="office_area_code,office_number",
            methods="get_telephone_number",
            name="TelephoneNumber",
        )

    def test_with_instance_vars(self) -> None:
        """Test extracting a class where extracted methods reference other extracted fields.

        Unlike test_simple where extracted methods are independent, this tests complex
        intra-class dependencies where methods need to access multiple extracted fields.
        Verifies the refactoring correctly establishes relationships between extracted
        members and updates method bodies to access fields through the new class.
        """
        self.refactor(
            "extract-class",
            source="Employee",
            fields="salary,bonus_percentage,deduction_rate,tax_rate",
            methods="calculate_gross_pay,calculate_net_pay,get_annual_compensation",
            name="Compensation",
        )

    def test_multiple_calls(self) -> None:
        """Test extracting a class where extracted methods are called from multiple locations.

        When extracted methods are invoked from various call sites, all references must
        be updated to access the method through the new extracted class. Tests that all
        call sites are properly updated, not just a subset.
        """
        self.refactor(
            "extract-class",
            source="Person",
            fields="office_area_code,office_number",
            methods="get_telephone_number",
            name="TelephoneNumber",
        )

    def test_with_decorators(self) -> None:
        """Test extracting a class that contains decorated methods (e.g., @property).

        When extracting methods with decorators, the decorators must be preserved
        and remain valid in the new class context. Tests proper handling of method
        metadata during extraction.
        """
        self.refactor(
            "extract-class",
            source="Employee",
            fields="street,city,state,zip_code",
            methods="full_address,update_street",
            name="Address",
        )

    def test_name_conflict(self) -> None:
        """Test that extract class raises error when proposed class name already exists.

        This error handling test verifies the refactoring prevents creating a new
        class that would conflict with an existing class. Critical for maintaining
        code integrity and preventing accidental shadowing or overwriting.
        """
        with pytest.raises(ValueError, match="Class .* already exists"):
            self.refactor(
                "extract-class",
                source="Person",
                fields="office_area_code,office_number",
                methods="get_telephone_number",
                name="TelephoneNumber",
            )

    @pytest.mark.skip(reason="Multi-file refactoring not yet implemented")
    def test_multi_file(self) -> None:
        """Test extract-class when field accesses span multiple files.

        Extracts PhoneNumber from Person and updates all call sites
        in directory.py and contacts.py from person.area_code to
        person.phone_number.area_code.
        """
        self.refactor_directory(
            "extract-class",
            target="person.py",
            source="Person",
            fields="area_code,number,extension",
            name="PhoneNumber",
        )
