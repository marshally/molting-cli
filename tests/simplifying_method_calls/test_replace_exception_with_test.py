"""Tests for Replace Exception with Test refactoring."""

from tests.conftest import RefactoringTestBase


class TestReplaceExceptionWithTest(RefactoringTestBase):
    """Tests for Replace Exception with Test refactoring."""

    fixture_category = "simplifying_method_calls/replace_exception_with_test"

    def test_simple(self) -> None:
        """Test replacing exception handling with a defensive test.

        This is the basic case: changing caller code from catching an exception
        to testing a condition first. Verifies the core transformation works
        before testing multiple call sites or instance variables.
        """
        self.refactor("replace-exception-with-test", target="get_value_for_period")

    def test_multiple_calls(self) -> None:
        """Test replacing exceptions with tests across multiple call sites.

        Unlike test_simple, this verifies that all callers that catch the exception
        are updated to test the condition first. Each caller must be consistently
        converted from exception handling to conditional testing.
        """
        self.refactor("replace-exception-with-test", target="get_value_for_period")

    def test_with_instance_vars(self) -> None:
        """Test replacing exception handling when instance variables are involved.

        Unlike test_simple, this tests the refactoring on a method that accesses
        instance state. Verifies that the test condition correctly evaluates
        instance variables instead of catching exceptions.
        """
        self.refactor("replace-exception-with-test", target="get_value_at_index")
