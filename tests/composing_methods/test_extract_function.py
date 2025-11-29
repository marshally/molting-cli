"""Tests for Extract Function refactoring.

Tests for the Extract Function refactoring, which extracts code
into a module-level function.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestExtractFunction(RefactoringTestBase):
    """Tests for Extract Function refactoring."""

    fixture_category = "composing_methods/extract_function"

    def test_simple(self) -> None:
        """Extract code into a module-level function."""
        self.refactor(
            "extract-function", target="DataProcessor::process#L4", name="normalize_string"
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test extract function when target function name already exists."""
        # Try to extract to normalize_string but it already exists at module level
        self.refactor(
            "extract-function", target="DataProcessor::process#L12", name="normalize_string"
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test extract function from decorated methods."""
        # Extract email formatting from @log_call decorated method
        self.refactor(
            "extract-function",
            target="EmailService::send_email#L19",
            name="format_email_address",
        )
