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
        """Replace the type code with subclasses."""
        self.refactor("replace-type-code-with-subclasses", target="Employee::type")
