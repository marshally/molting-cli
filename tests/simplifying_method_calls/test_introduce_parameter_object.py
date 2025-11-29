"""Tests for Introduce Parameter Object refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestIntroduceParameterObject(RefactoringTestBase):
    """Tests for Introduce Parameter Object refactoring."""

    fixture_category = "simplifying_method_calls/introduce_parameter_object"

    def test_simple(self) -> None:
        """Replace parameters with a parameter object."""
        self.refactor(
            "introduce-parameter-object",
            target="flow_between",
            params="start_date,end_date",
            name="DateRange",
        )

    def test_multiple_calls(self) -> None:
        """Test introduce parameter object with multiple call sites."""
        self.refactor(
            "introduce-parameter-object",
            target="flow_between",
            params="start_date,end_date",
            name="DateRange",
        )

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test introduce parameter object with local variables."""
        self.refactor(
            "introduce-parameter-object",
            target="ReportGenerator::generate_summary",
            params="start_row,end_row,include_headers,include_totals",
            name="ReportConfig",
        )

    def test_name_conflict(self) -> None:
        """Test introduce parameter object when class name already exists."""
        self.refactor(
            "introduce-parameter-object",
            target="flow_between",
            params="start_date,end_date",
            name="DateRange",
        )
