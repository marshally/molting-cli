"""
Tests for Organizing Data refactorings.

This module tests refactorings that organize data structures, improve encapsulation,
and replace primitives with objects.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestSelfEncapsulateField(RefactoringTestBase):
    """Tests for Self Encapsulate Field refactoring."""

    fixture_category = "organizing_data/self_encapsulate_field"

    def test_simple(self) -> None:
        """Create getter and setter methods for a field."""
        from molting.cli import refactor_file

        assert self.test_file is not None
        refactor_file("self-encapsulate-field", self.test_file, target="Range::low")
        refactor_file("self-encapsulate-field", self.test_file, target="Range::high")
        self.assert_matches_expected()

    def test_with_decorators(self) -> None:
        """Test self-encapsulate-field with decorated methods."""
        from molting.cli import refactor_file

        assert self.test_file is not None
        refactor_file("self-encapsulate-field", self.test_file, target="Range::low")
        refactor_file("self-encapsulate-field", self.test_file, target="Range::high")
        self.assert_matches_expected()

    def test_multiple_calls(self) -> None:
        """Test self-encapsulate-field with multiple call sites."""
        from molting.cli import refactor_file

        assert self.test_file is not None
        refactor_file("self-encapsulate-field", self.test_file, target="Range::low")
        refactor_file("self-encapsulate-field", self.test_file, target="Range::high")
        self.assert_matches_expected()


class TestReplaceDataValueWithObject(RefactoringTestBase):
    """Tests for Replace Data Value with Object refactoring."""

    fixture_category = "organizing_data/replace_data_value_with_object"

    def test_simple(self) -> None:
        """Turn a data item into an object."""
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    def test_with_locals(self) -> None:
        """Test replace data value with object with local variables."""
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    def test_with_instance_vars(self) -> None:
        """Test replace-data-value-with-object with instance variables."""
        self.refactor(
            "replace-data-value-with-object", target="Invoice::customer_name", name="CustomerInfo"
        )

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update all call sites"
    )
    def test_multiple_calls(self) -> None:
        """Test replace-data-value-with-object with multiple call sites."""
        self.refactor("replace-data-value-with-object", target="Order::customer", name="Customer")

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace data value with object when target name already exists."""
        with pytest.raises(ValueError, match="Class.*Customer.*already exists"):
            self.refactor(
                "replace-data-value-with-object", target="Order::customer", name="Customer"
            )


class TestChangeValueToReference(RefactoringTestBase):
    """Tests for Change Value to Reference refactoring."""

    fixture_category = "organizing_data/change_value_to_reference"

    def test_simple(self) -> None:
        """Turn a value object into a reference object."""
        self.refactor("change-value-to-reference", target="Customer")

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-value-to-reference with instance variables."""
        self.refactor("change-value-to-reference", target="Product")


class TestChangeReferenceToValue(RefactoringTestBase):
    """Tests for Change Reference to Value refactoring."""

    fixture_category = "organizing_data/change_reference_to_value"

    def test_simple(self) -> None:
        """Turn a reference object into a value object."""
        self.refactor("change-reference-to-value", target="Currency")

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-reference-to-value with instance variables."""
        self.refactor("change-reference-to-value", target="Money")


class TestReplaceArrayWithObject(RefactoringTestBase):
    """Tests for Replace Array with Object refactoring."""

    fixture_category = "organizing_data/replace_array_with_object"

    def test_simple(self) -> None:
        """Replace an array with an object that has a field for each element."""
        self.refactor(
            "replace-array-with-object", target="analyze_performance::row", name="Performance"
        )

    @pytest.mark.skip(
        reason=(
            "Implementation needed for with_locals - only transforms first function, "
            "not all functions with same parameter"
        )
    )
    def test_with_locals(self) -> None:
        """Test replace array with object with local variables."""
        self.refactor(
            "replace-array-with-object", target="analyze_performance::row", name="Performance"
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace array with object when target name already exists."""
        with pytest.raises(ValueError, match="Class.*Performance.*already exists"):
            self.refactor(
                "replace-array-with-object", target="analyze_performance::row", name="Performance"
            )


class TestDuplicateObservedData(RefactoringTestBase):
    """Tests for Duplicate Observed Data refactoring."""

    fixture_category = "organizing_data/duplicate_observed_data"

    def test_simple(self) -> None:
        """Copy data from domain object to GUI object and set up observer pattern."""
        self.refactor(
            "duplicate-observed-data", target="IntervalWindow::start_field", domain="Interval"
        )


class TestChangeUnidirectionalAssociationToBidirectional(RefactoringTestBase):
    """Tests for Change Unidirectional Association to Bidirectional refactoring."""

    fixture_category = "organizing_data/change_unidirectional_association_to_bidirectional"

    def test_simple(self) -> None:
        """Add back pointers and change modifiers to update both sets."""
        self.refactor(
            "change-unidirectional-association-to-bidirectional",
            target="Order::customer",
            back="orders",
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-unidirectional-association-to-bidirectional with instance variables."""
        self.refactor(
            "change-unidirectional-association-to-bidirectional",
            target="Team::manager",
            back="teams",
        )


class TestChangeBidirectionalAssociationToUnidirectional(RefactoringTestBase):
    """Tests for Change Bidirectional Association to Unidirectional refactoring."""

    fixture_category = "organizing_data/change_bidirectional_association_to_unidirectional"

    def test_simple(self) -> None:
        """Remove back pointers."""
        self.refactor(
            "change-bidirectional-association-to-unidirectional", target="Customer::_orders"
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test change-bidirectional-association-to-unidirectional with instance variables."""
        self.refactor(
            "change-bidirectional-association-to-unidirectional", target="Owner::_projects"
        )


class TestReplaceMagicNumberWithSymbolicConstant(RefactoringTestBase):
    """Tests for Replace Magic Number with Symbolic Constant refactoring."""

    fixture_category = "organizing_data/replace_magic_number_with_symbolic_constant"

    def test_simple(self) -> None:
        """Create a constant, name it after the meaning, and replace the number with it."""
        self.refactor(
            "replace-magic-number-with-symbolic-constant",
            target="potential_energy#L2",
            name="GRAVITATIONAL_CONSTANT",
        )

    @pytest.mark.skip(
        reason=(
            "Implementation needed for with_locals - only replaces in targeted function, "
            "not all occurrences"
        )
    )
    def test_with_locals(self) -> None:
        """Test replace magic number with symbolic constant with local variables."""
        self.refactor(
            "replace-magic-number-with-symbolic-constant",
            target="potential_energy#L5",
            name="GRAVITATIONAL_CONSTANT",
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing constant"
    )
    def test_name_conflict(self) -> None:
        """Test replace magic number with symbolic constant when target name already exists."""
        with pytest.raises(ValueError, match="Constant.*GRAVITATIONAL_CONSTANT.*already exists"):
            self.refactor(
                "replace-magic-number-with-symbolic-constant",
                target="potential_energy#L2",
                name="GRAVITATIONAL_CONSTANT",
            )


class TestEncapsulateField(RefactoringTestBase):
    """Tests for Encapsulate Field refactoring."""

    fixture_category = "organizing_data/encapsulate_field"

    def test_simple(self) -> None:
        """Make the field private and provide accessors."""
        self.refactor("encapsulate-field", target="Person::name")

    def test_with_decorators(self) -> None:
        """Test encapsulate-field with decorated methods."""
        self.refactor("encapsulate-field", target="Person::name")

    def test_multiple_calls(self) -> None:
        """Test encapsulate-field with multiple call sites."""
        self.refactor("encapsulate-field", target="Person::name")


class TestEncapsulateCollection(RefactoringTestBase):
    """Tests for Encapsulate Collection refactoring."""

    fixture_category = "organizing_data/encapsulate_collection"

    def test_simple(self) -> None:
        """Make the method return a read-only view and provide add/remove methods."""
        self.refactor("encapsulate-collection", target="Person::courses")

    def test_with_decorators(self) -> None:
        """Test encapsulate-collection with decorated methods."""
        self.refactor("encapsulate-collection", target="Person::courses")

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update external call sites"
    )
    def test_multiple_calls(self) -> None:
        """Test encapsulate-collection with multiple call sites."""
        self.refactor("encapsulate-collection", target="Person::courses")


class TestReplaceTypeCodeWithClass(RefactoringTestBase):
    """Tests for Replace Type Code with Class refactoring."""

    fixture_category = "organizing_data/replace_type_code_with_class"

    def test_simple(self) -> None:
        """Replace the type code with a new class."""
        self.refactor(
            "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
        )

    @pytest.mark.skip(reason="Fixture loading broken for with_instance_vars tests")
    def test_with_instance_vars(self) -> None:
        """Test replace-type-code-with-class with instance variables."""
        self.refactor("replace-type-code-with-class", target="Task::priority", name="Priority")

    @pytest.mark.skip(
        reason="Implementation needed for multiple_calls - doesn't update type code references"
    )
    def test_multiple_calls(self) -> None:
        """Test replace-type-code-with-class with multiple call sites."""
        self.refactor(
            "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace type code with class when target name already exists."""
        with pytest.raises(ValueError, match="Class.*BloodGroup.*already exists"):
            self.refactor(
                "replace-type-code-with-class", target="Person::blood_group", name="BloodGroup"
            )


class TestReplaceTypeCodeWithSubclasses(RefactoringTestBase):
    """Tests for Replace Type Code with Subclasses refactoring."""

    fixture_category = "organizing_data/replace_type_code_with_subclasses"

    def test_simple(self) -> None:
        """Replace the type code with subclasses."""
        self.refactor("replace-type-code-with-subclasses", target="Employee::type")


class TestReplaceTypeCodeWithStateStrategy(RefactoringTestBase):
    """Tests for Replace Type Code with State/Strategy refactoring."""

    fixture_category = "organizing_data/replace_type_code_with_state_strategy"

    def test_simple(self) -> None:
        """Replace the type code with a state object."""
        self.refactor(
            "replace-type-code-with-state-strategy", target="Employee::type", name="EmployeeType"
        )

    @pytest.mark.skip(
        reason="Implementation needed for name_conflict - should detect existing class"
    )
    def test_name_conflict(self) -> None:
        """Test replace type code with state/strategy when target name already exists."""
        with pytest.raises(ValueError, match="Class.*EmployeeType.*already exists"):
            self.refactor(
                "replace-type-code-with-state-strategy",
                target="Employee::type",
                name="EmployeeType",
            )
