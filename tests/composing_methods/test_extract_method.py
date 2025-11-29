"""Tests for Extract Method refactoring.

Tests for the Extract Method refactoring, which extracts a code fragment
into its own new method with a clear, intention-revealing name.
"""

from tests.conftest import RefactoringTestBase


class TestExtractMethod(RefactoringTestBase):
    """Tests for Extract Method refactoring."""

    fixture_category = "composing_methods/extract_method"

    def test_simple(self) -> None:
        """Test basic extract method refactoring.

        This is the simplest case: extracting a simple code block (the banner printing)
        from a method into its own method. The extracted method should have no parameters
        or return values.
        """
        self.refactor("extract-method", target="Order::print_owing#L9-L12", name="print_banner")
