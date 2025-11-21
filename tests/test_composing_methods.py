"""
Tests for Composing Methods refactorings.

This module tests refactorings that improve the internal structure of methods
by extracting, inlining, and reorganizing code.
"""
from tests.conftest import RefactoringTestBase


class TestExtractMethod(RefactoringTestBase):
    """Tests for Extract Method refactoring."""

    fixture_category = "composing_methods/extract_method"

    def test_simple(self):
        """Extract a code block into a method."""
        # Extract print banner
        self.refactor("extract-method", target="Order::print_owing#L10-L12", name="print_banner")


class TestExtractFunction(RefactoringTestBase):
    """Tests for Extract Function refactoring."""

    fixture_category = "composing_methods/extract_function"

    def test_simple(self):
        """Extract code into a module-level function."""
        self.refactor(
            "extract-function", target="DataProcessor::process#L4", name="normalize_string"
        )


class TestInlineMethod(RefactoringTestBase):
    """Tests for Inline Method refactoring."""

    fixture_category = "composing_methods/inline_method"

    def test_simple(self):
        """Inline a simple method whose body is as clear as its name."""
        self.refactor("inline-method", target="Person::more_than_five_late_deliveries")


class TestInlineTemp(RefactoringTestBase):
    """Tests for Inline Temp refactoring."""

    fixture_category = "composing_methods/inline_temp"

    def test_simple(self):
        """Replace a temp variable with its expression."""
        self.refactor("inline-temp", target="calculate_total::temp_value")


class TestReplaceTempWithQuery(RefactoringTestBase):
    """Tests for Replace Temp with Query refactoring."""

    fixture_category = "composing_methods/replace_temp_with_query"

    def test_simple(self):
        """Extract expression into a method and replace temp."""
        self.refactor("replace-temp-with-query", target="Order::get_price::base_price")


class TestIntroduceExplainingVariable(RefactoringTestBase):
    """Tests for Introduce Explaining Variable refactoring."""

    fixture_category = "composing_methods/introduce_explaining_variable"

    def test_simple(self):
        """Put the entire return expression into a named temp variable."""
        self.refactor(
            "introduce-explaining-variable", target="calculate_total#L2", name="total"
        )


class TestSplitTemporaryVariable(RefactoringTestBase):
    """Tests for Split Temporary Variable refactoring."""

    fixture_category = "composing_methods/split_temporary_variable"

    def test_simple(self):
        """Split a temp variable assigned multiple times."""
        self.refactor("split-temporary-variable", target="calculate_distance::temp")


class TestRemoveAssignmentsToParameters(RefactoringTestBase):
    """Tests for Remove Assignments to Parameters refactoring."""

    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_simple(self):
        """Use a temp variable instead of assigning to parameters."""
        self.refactor("remove-assignments-to-parameters", target="discount")


class TestReplaceMethodWithMethodObject(RefactoringTestBase):
    """Tests for Replace Method with Method Object refactoring."""

    fixture_category = "composing_methods/replace_method_with_method_object"

    def test_simple(self):
        """Turn a long method into its own object."""
        self.refactor("replace-method-with-method-object", target="Account::gamma")


class TestSubstituteAlgorithm(RefactoringTestBase):
    """Tests for Substitute Algorithm refactoring."""

    fixture_category = "composing_methods/substitute_algorithm"

    def test_simple(self):
        """Replace an algorithm with a clearer one."""
        self.refactor("substitute-algorithm", target="found_person")
