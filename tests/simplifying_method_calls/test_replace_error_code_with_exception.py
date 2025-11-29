"""Tests for Replace Error Code with Exception refactoring."""


from tests.conftest import RefactoringTestBase


class TestReplaceErrorCodeWithException(RefactoringTestBase):
    """Tests for Replace Error Code with Exception refactoring."""

    fixture_category = "simplifying_method_calls/replace_error_code_with_exception"

    def test_simple(self) -> None:
        """Throw an exception instead of returning an error code."""
        self.refactor("replace-error-code-with-exception", target="withdraw")

    def test_multiple_calls(self) -> None:
        """Test replace error code with exception with multiple call sites."""
        self.refactor("replace-error-code-with-exception", target="withdraw")

    def test_with_instance_vars(self) -> None:
        """Test replace error code with exception with instance variables."""
        self.refactor("replace-error-code-with-exception", target="process_withdrawal")
