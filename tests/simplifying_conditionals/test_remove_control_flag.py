"""
Tests for Remove Control Flag refactoring.

This refactoring replaces a control flag variable with break or return.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestRemoveControlFlag(RefactoringTestBase):
    """Tests for Remove Control Flag refactoring."""

    fixture_category = "simplifying_conditionals/remove_control_flag"

    def test_simple(self) -> None:
        """Test removing a simple control flag variable from a loop.

        This is the simplest case: a boolean flag used to exit a loop is replaced with
        a break or return statement. Verifies the core transformation works before testing
        with local variables, instance variables, or decorated methods.
        """
        self.refactor("remove-control-flag", target="check_security::found")

    @pytest.mark.skip(
        reason="Command needs enhancement: analyze return statement to determine which variables to return. "
        "Use VariableLifetimeAnalyzer to determine 'count' is used after loop and should be in return tuple. "
        "VariableLifetimeAnalyzer available in molting/core/variable_lifetime_analyzer.py"
    )
    def test_with_locals(self) -> None:
        """Test removing a control flag when local variables are involved.

        Unlike test_simple, this tests flag removal in a context with local variables
        that interact with the flag logic. Verifies that variable scope and dependencies
        are correctly handled when replacing the flag with break/return.
        """
        self.refactor("remove-control-flag", target="find_matching_product::found")

    def test_with_instance_vars(self) -> None:
        """Test removing a control flag in an instance method using self variables.

        This tests flag removal in an instance method where the flag logic may interact
        with instance variables (self.field). Verifies that instance variable access
        is preserved when replacing the control flag.
        """
        self.refactor("remove-control-flag", target="SecurityChecker::check_security::found")

    def test_with_decorators(self) -> None:
        """Test removing a control flag from a method with decorators.

        This tests flag removal when the containing method has decorators (e.g., @property,
        @cached, @staticmethod, etc.). Verifies that decorators on the method are preserved
        and don't interfere with the flag removal logic.
        """
        self.refactor("remove-control-flag", target="SecurityChecker::is_secure::found")
