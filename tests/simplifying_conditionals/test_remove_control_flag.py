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
        """Replace a control flag variable with break or return."""
        self.refactor("remove-control-flag", target="check_security::found")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test remove control flag with local variables."""
        self.refactor("remove-control-flag", target="find_matching_product::found")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test remove control flag with instance variables."""
        self.refactor("remove-control-flag", target="SecurityChecker::check_security::found")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test remove control flag with decorated methods."""
        self.refactor("remove-control-flag", target="SecurityChecker::is_secure::found")
