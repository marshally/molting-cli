"""Tests for Extract Method refactoring.

Tests for the Extract Method refactoring, which extracts a code block
into a new method.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestExtractMethod(RefactoringTestBase):
    """Tests for Extract Method refactoring."""

    fixture_category = "composing_methods/extract_method"

    def test_simple(self) -> None:
        """Extract a code block into a new method."""
        # Extract print banner (lines 9-12: comment + 3 print statements)
        self.refactor("extract-method", target="Order::print_owing#L9-L12", name="print_banner")

    def test_with_locals(self) -> None:
        """Test extract method with local variables."""
        # Extract calculation that uses and modifies local variable 'outstanding'
        self.refactor(
            "extract-method",
            target="Order::print_owing#L18-L19",
            name="calculate_outstanding",
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test extract method with instance variables."""
        # Extract subtotal calculation that uses self.items
        self.refactor(
            "extract-method",
            target="Order::calculate_total#L13-L15",
            name="calculate_subtotal",
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test extract method when target method name already exists."""
        # Try to extract to print_banner but it already exists
        self.refactor("extract-method", target="Order::print_owing#L13-L15", name="print_banner")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test extract method with decorated methods."""
        # Extract pricing calculation from @property decorated method
        self.refactor(
            "extract-method",
            target="Product::display_info#L23-L25",
            name="_calculate_pricing",
        )
