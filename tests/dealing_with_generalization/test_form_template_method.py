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
        """Test basic formation of a template method from similar algorithms.

        Extracts the common structure of get_bill_amount from ResidentialSite and
        LifelineSite into a template method in the superclass Site. The invariant
        algorithm structure is in the superclass, with variant steps delegated to
        abstract methods in subclasses. This is the simplest case with clear
        algorithmic similarity.
        """
        self.refactor(
            "form-template-method",
            targets="ResidentialSite::get_bill_amount,LifelineSite::get_bill_amount",
            name="get_bill_amount",
            steps="base:get_base_amount,tax:get_tax_amount",
        )

    @pytest.mark.skip(reason="Requires template method extraction with local variable handling in class hierarchies - implementation planned")
    def test_with_locals(self) -> None:
        """Test form-template-method when methods use local variables.

        Unlike test_simple, this tests extracting methods that declare and use
        local variables within their implementations. The refactoring must properly
        handle these locals: either converting them to instance variables or
        managing their scope across the template method and abstract method calls.
        """
        self.refactor(
            "form-template-method",
            targets="ResidentialSite::get_bill_amount,LifelineSite::get_bill_amount",
            name="get_bill_amount",
            steps="base:get_base_amount,tax:get_tax_amount",
        )
