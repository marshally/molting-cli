"""Tests for Introduce Parameter Object refactoring."""


from tests.conftest import RefactoringTestBase


class TestIntroduceParameterObject(RefactoringTestBase):
    """Tests for Introduce Parameter Object refactoring."""

    fixture_category = "simplifying_method_calls/introduce_parameter_object"

    def test_simple(self) -> None:
        """Test introducing a parameter object to group related parameters.

        This is the basic case: replacing multiple related parameters
        (start_date, end_date) with a single parameter object (DateRange).
        Verifies the core transformation works before testing multiple call sites.
        """
        self.refactor(
            "introduce-parameter-object",
            target="flow_between",
            params="start_date,end_date",
            name="DateRange",
        )

    def test_multiple_calls(self) -> None:
        """Test introducing a parameter object across multiple call sites.

        Unlike test_simple, this verifies that all method call sites are updated
        to construct and pass the parameter object instead of individual parameters.
        Each caller must be consistently converted to use the new object.
        """
        self.refactor(
            "introduce-parameter-object",
            target="flow_between",
            params="start_date,end_date",
            name="DateRange",
        )

    def test_with_locals(self) -> None:
        """Test introducing a parameter object when local variables are involved.

        Unlike test_simple, this tests when the method body uses local variables
        that depend on the original parameters. The refactoring must correctly
        extract these locals from the parameter object.
        """
        self.refactor(
            "introduce-parameter-object",
            target="ReportGenerator::generate_summary",
            params="start_row,end_row,include_headers,include_totals",
            name="ReportConfig",
        )

    def test_name_conflict(self) -> None:
        """Test introducing a parameter object when the class name already exists.

        This is an edge case where the parameter object class name (DateRange)
        would conflict with an existing class. The refactoring must handle this
        gracefully by detecting the conflict.
        """
        self.refactor(
            "introduce-parameter-object",
            target="flow_between",
            params="start_date,end_date",
            name="DateRange",
        )
