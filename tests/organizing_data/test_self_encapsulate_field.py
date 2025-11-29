"""
Tests for Self Encapsulate Field refactoring.

This test module verifies the self-encapsulate-field refactoring, which creates
getter and setter methods for class fields.
"""

from tests.conftest import RefactoringTestBase


class TestSelfEncapsulateField(RefactoringTestBase):
    """Tests for Self Encapsulate Field refactoring."""

    fixture_category = "organizing_data/self_encapsulate_field"

    def test_simple(self) -> None:
        """Test basic self-encapsulate field on simple public fields.

        This is the simplest case: converting public fields to private with
        getter/setter methods. Verifies the core transformation works on fields
        without existing accessors or decorators before testing more complex cases.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None
        refactor_file("self-encapsulate-field", self.test_file, target="Range::low")
        refactor_file("self-encapsulate-field", self.test_file, target="Range::high")
        self.assert_matches_expected()

    def test_with_decorators(self) -> None:
        """Test self-encapsulate-field when class has decorated methods like @property.

        Unlike test_simple, this verifies that existing decorated methods or properties
        are properly handled and don't conflict with the generated getter/setter methods.
        Important for classes that already use Python's property protocol.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None
        refactor_file("self-encapsulate-field", self.test_file, target="Range::low")
        refactor_file("self-encapsulate-field", self.test_file, target="Range::high")
        self.assert_matches_expected()

    def test_multiple_calls(self) -> None:
        """Test self-encapsulate-field when fields are accessed from multiple locations.

        Unlike test_simple which tests transformation in isolation, this verifies that
        all internal references to the field are properly updated to use the new
        getter/setter methods throughout the class, maintaining consistency across call sites.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None
        refactor_file("self-encapsulate-field", self.test_file, target="Range::low")
        refactor_file("self-encapsulate-field", self.test_file, target="Range::high")
        self.assert_matches_expected()
