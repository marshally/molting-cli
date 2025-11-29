"""
Tests for Form Template Method refactoring.

This refactoring puts the invariant parts of an algorithm in the superclass
and delegates the variant parts to abstract methods in subclasses.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestFormTemplateMethod(RefactoringTestBase):
    """Tests for Form Template Method refactoring."""

    fixture_category = "dealing_with_generalization/form_template_method"

    def test_simple(self) -> None:
        """Put the invariant parts of the algorithm in the superclass."""
        self.refactor(
            "form-template-method",
            targets="ResidentialSite::get_bill_amount,LifelineSite::get_bill_amount",
            name="get_bill_amount",
        )

    @pytest.mark.skip(reason="Implementation needed for local variables")
    def test_with_locals(self) -> None:
        """Test form template method with local variables."""
        self.refactor(
            "form-template-method",
            targets="ResidentialSite::get_bill_amount,LifelineSite::get_bill_amount",
            name="get_bill_amount",
        )
