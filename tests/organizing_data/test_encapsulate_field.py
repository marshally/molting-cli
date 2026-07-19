"""
Tests for Encapsulate Field refactoring.

This test module verifies the encapsulate-field refactoring,
which makes fields private and provides accessor methods.
"""


from tests.conftest import RefactoringTestBase


class TestEncapsulateField(RefactoringTestBase):
    """Tests for Encapsulate Field refactoring."""

    fixture_category = "organizing_data/encapsulate_field"

    def test_simple(self) -> None:
        """Test basic encapsulate field on a public field.

        This is the simplest case: converting a public field to private with getter/setter
        methods. Verifies the core transformation works before testing fields with existing
        accessors or decorators.
        """
        self.refactor("encapsulate-field", target="Person::name")

    def test_with_decorators(self) -> None:
        """Test encapsulate field when class has existing decorated accessor methods.

        Unlike test_simple, this verifies that methods with decorators like @property
        are properly handled and don't conflict with the generated getter/setter methods.
        Important for classes that already use Python's property protocol.
        """
        self.refactor("encapsulate-field", target="Person::name")

    def test_multiple_calls(self) -> None:
        """Test encapsulate field when field is accessed from multiple locations.

        Unlike test_simple, this verifies that all external references to the field are
        properly updated to use the new getter/setter methods, maintaining consistency
        across all call sites that access the field.
        """
        self.refactor("encapsulate-field", target="Person::name")

    def test_multi_file(self) -> None:
        """Test encapsulate-field when field accesses span multiple files.

        This verifies that when a field is encapsulated with getter/setter methods,
        all field accesses across multiple files are updated to use the property
        accessors instead of direct field access.
        """
        self.refactor_directory(
            "encapsulate-field",
            target="Product::price",
        )
