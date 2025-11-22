"""
Tests for Composing Methods refactorings.

This module tests refactorings that improve the internal structure of methods
by extracting, inlining, and reorganizing code.
"""

import pytest

from tests.conftest import RefactoringTestBase


class TestExtractMethod(RefactoringTestBase):
    """Tests for Extract Method refactoring."""

    fixture_category = "composing_methods/extract_method"

    def test_simple(self) -> None:
        """Extract a code block into a new method."""
        # Extract print banner (lines 9-12: comment + 3 print statements)
        self.refactor("extract-method", target="Order::print_owing#L9-L12", name="print_banner")


@pytest.mark.skip(reason="No implementation yet")
class TestExtractFunction(RefactoringTestBase):
    """Tests for Extract Function refactoring."""

    fixture_category = "composing_methods/extract_function"

    def test_simple(self) -> None:
        """Extract code into a module-level function."""
        self.refactor(
            "extract-function", target="DataProcessor::process#L4", name="normalize_string"
        )


@pytest.mark.skip(reason="No implementation yet")
class TestInlineMethod(RefactoringTestBase):
    """Tests for Inline Method refactoring."""

    fixture_category = "composing_methods/inline_method"

    def test_simple(self) -> None:
        """Inline a simple method whose body is as clear as its name."""
        self.refactor("inline-method", target="Person::more_than_five_late_deliveries")


@pytest.mark.skip(reason="No implementation yet")
class TestInlineTemp(RefactoringTestBase):
    """Tests for Inline Temp refactoring."""

    fixture_category = "composing_methods/inline_temp"

    def test_simple(self) -> None:
        """Replace a temp variable with its expression."""
        self.refactor("inline-temp", target="calculate_total::base_price")


@pytest.mark.skip(reason="No implementation yet")
class TestReplaceTempWithQuery(RefactoringTestBase):
    """Tests for Replace Temp with Query refactoring."""

    fixture_category = "composing_methods/replace_temp_with_query"

    def test_simple(self) -> None:
        """Extract expression into a method and replace temp."""
        self.refactor("replace-temp-with-query", target="Order::get_price::base_price")


@pytest.mark.skip(reason="No implementation yet")
class TestIntroduceExplainingVariable(RefactoringTestBase):
    """Tests for Introduce Explaining Variable refactoring."""

    fixture_category = "composing_methods/introduce_explaining_variable"

    def test_simple(self) -> None:
        """Put complex expressions into named temp variables."""
        self.refactor(
            "introduce-explaining-variable", target="calculate_total#L2", name="base_price"
        )
        self.refactor(
            "introduce-explaining-variable", target="calculate_total#L3", name="quantity_discount"
        )
        self.refactor("introduce-explaining-variable", target="calculate_total#L4", name="shipping")


@pytest.mark.skip(reason="No implementation yet")
class TestSplitTemporaryVariable(RefactoringTestBase):
    """Tests for Split Temporary Variable refactoring."""

    fixture_category = "composing_methods/split_temporary_variable"

    def test_simple(self) -> None:
        """Split a temp variable assigned multiple times."""
        self.refactor("split-temporary-variable", target="calculate_distance::temp")


@pytest.mark.skip(reason="No implementation yet")
class TestRemoveAssignmentsToParameters(RefactoringTestBase):
    """Tests for Remove Assignments to Parameters refactoring."""

    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_simple(self) -> None:
        """Use a temp variable instead of assigning to parameters."""
        self.refactor("remove-assignments-to-parameters", target="discount")


@pytest.mark.skip(reason="No implementation yet")
class TestReplaceMethodWithMethodObject(RefactoringTestBase):
    """Tests for Replace Method with Method Object refactoring."""

    fixture_category = "composing_methods/replace_method_with_method_object"

    def test_simple(self) -> None:
        """Turn a long method into its own object."""
        self.refactor("replace-method-with-method-object", target="Account::gamma")


@pytest.mark.skip(reason="No implementation yet")
class TestSubstituteAlgorithm(RefactoringTestBase):
    """Tests for Substitute Algorithm refactoring."""

    fixture_category = "composing_methods/substitute_algorithm"

    def test_simple(self) -> None:
        """Replace an algorithm with a clearer one."""
        self.refactor("substitute-algorithm", target="found_person")
