"""Tests for Replace Error Code with Exception refactoring."""


from tests.conftest import RefactoringTestBase


class TestReplaceErrorCodeWithException(RefactoringTestBase):
    """Tests for Replace Error Code with Exception refactoring."""

    fixture_category = "simplifying_method_calls/replace_error_code_with_exception"

    def test_simple(self) -> None:
        """Test replacing error code returns with exceptions in the basic case.

        This is the simplest case: changing a method that returns an error code
        to throw an exception instead. Verifies the core transformation works
        before testing multiple call sites or instance variables.
        """
        self.refactor("replace-error-code-with-exception", target="withdraw")

    def test_multiple_calls(self) -> None:
        """Test replacing error codes with exceptions across multiple call sites.

        Unlike test_simple, this verifies that all call sites that checked the
        error code return value are updated to handle exceptions instead. This is
        critical to ensure all error handling paths are updated consistently.
        """
        self.refactor("replace-error-code-with-exception", target="withdraw")

    def test_with_instance_vars(self) -> None:
        """Test replacing error codes when the method uses instance variables.

        Unlike test_simple, this tests the refactoring on a method that accesses
        instance state. Verifies that instance references remain valid after
        changing from error code returns to exception throwing.
        """
        self.refactor("replace-error-code-with-exception", target="process_withdrawal")
