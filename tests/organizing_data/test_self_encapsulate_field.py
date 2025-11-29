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
