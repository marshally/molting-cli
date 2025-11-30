"""Tests for Preserve Whole Object refactoring."""

import pytest

from tests.conftest import RefactoringTestBase


class TestPreserveWholeObject(RefactoringTestBase):
    """Tests for Preserve Whole Object refactoring."""

    fixture_category = "simplifying_method_calls/preserve_whole_object"

    def test_simple(self) -> None:
        """Test passing a whole object instead of individual extracted values.

        This is the basic case: replacing multiple parameter extractions
        (e.g., plan.start, plan.end) with a single parameter (plan).
        Verifies the core transformation works before testing multiple call sites.
        """
        self.refactor("preserve-whole-object", target="within_plan")

    def test_multiple_calls(self) -> None:
        """Test preserving whole object when called from multiple locations.

        Unlike test_simple, this verifies that all call sites are updated to
        pass the whole object instead of extracted values. Each caller must
        change its signature when the method signature changes.
        """
        self.refactor("preserve-whole-object", target="within_plan")

    @pytest.mark.skip(
        reason="Requires object property extraction to local variables - implementation planned"
    )
    def test_with_locals(self) -> None:
        """Test preserving whole object when local variables are involved.

        Unlike test_simple, this tests when extracted values are assigned to
        local variables. The refactoring must handle local variable extraction
        from the passed object.
        """
        self.refactor("preserve-whole-object", target="can_withdraw")
