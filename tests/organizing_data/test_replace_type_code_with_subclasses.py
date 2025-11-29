"""
Tests for Replace Type Code with Subclasses refactoring.

This test module verifies the replace-type-code-with-subclasses refactoring,
which replaces type codes with subclasses.
"""


from tests.conftest import RefactoringTestBase


class TestReplaceTypeCodeWithSubclasses(RefactoringTestBase):
    """Tests for Replace Type Code with Subclasses refactoring."""

    fixture_category = "organizing_data/replace_type_code_with_subclasses"

    def test_simple(self) -> None:
        """Test basic replacement of a type code with inheritance-based subclasses.

        This is the simplest case: converting a type code field into separate subclasses
        of the original class. Verifies the core transformation creates proper subclass
        hierarchy before testing more complex inheritance scenarios.
        """
        self.refactor("replace-type-code-with-subclasses", target="Employee::type")
