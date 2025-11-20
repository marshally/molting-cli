"""Tests for Composing Methods refactorings.

This module tests refactorings from the "Composing Methods" category,
which improve the internal structure of methods.
"""

from tests.conftest import RefactoringTestBase


class TestExtractMethod(RefactoringTestBase):
    """Test Extract Method refactoring.

    Extract Method turns a code fragment into a method whose name
    explains the purpose of the method.
    """

    fixture_category = "composing_methods/extract_method"

    def test_simple(self):
        """Extract a simple code block with no local variables."""
        self.refactor(
            "extract-method",
            target="Order::print_owing#L6-L8",
            name="print_banner"
        )

    def test_with_locals(self):
        """Extract code that uses local variables."""
        self.refactor(
            "extract-method",
            target="Order::print_owing#L10-L12",
            name="calculate_outstanding"
        )

    def test_with_return_value(self):
        """Extract code that returns a value."""
        self.refactor(
            "extract-method",
            target="Calculator::compute#L5-L7",
            name="apply_discount"
        )


class TestExtractFunction(RefactoringTestBase):
    """Test Extract Function refactoring.

    Extract Function creates a module-level function from code that
    doesn't need instance state.
    """

    fixture_category = "composing_methods/extract_function"

    def test_simple(self):
        """Extract method to module-level function."""
        self.refactor(
            "extract-function",
            target="DataProcessor::process#L4",
            name="normalize_string"
        )


class TestInlineMethod(RefactoringTestBase):
    """Test Inline Method refactoring.

    Inline Method replaces calls to a method with the method's body
    when the body is as clear as the name.
    """

    fixture_category = "composing_methods/inline_method"

    def test_simple(self):
        """Inline a simple one-line method."""
        self.refactor(
            "inline-method",
            target="Person::more_than_five_late_deliveries"
        )


class TestInlineTemp(RefactoringTestBase):
    """Test Inline Temp refactoring.

    Inline Temp replaces a temporary variable with the expression
    that creates it.
    """

    fixture_category = "composing_methods/inline_temp"

    def test_simple(self):
        """Inline a simple temporary variable."""
        self.refactor(
            "inline-temp",
            target="calculate_total::base_price"
        )


class TestReplaceTempWithQuery(RefactoringTestBase):
    """Test Replace Temp with Query refactoring.

    Replace Temp with Query extracts the expression into a method
    and replaces all references to the temp with method calls.
    """

    fixture_category = "composing_methods/replace_temp_with_query"

    def test_simple(self):
        """Replace a temporary variable with a query method."""
        self.refactor(
            "replace-temp-with-query",
            target="Order::get_price::base_price"
        )


class TestIntroduceExplainingVariable(RefactoringTestBase):
    """Test Introduce Explaining Variable refactoring.

    Introduce Explaining Variable puts the result of a complex expression
    into a temporary variable with a name that explains the purpose.
    """

    fixture_category = "composing_methods/introduce_explaining_variable"

    def test_complex_expression(self):
        """Break down complex expression into explaining variables."""
        self.refactor(
            "introduce-explaining-variable",
            target="calculate_total#L2",
            name="base_price"
        )


class TestSplitTemporaryVariable(RefactoringTestBase):
    """Test Split Temporary Variable refactoring.

    Split Temporary Variable creates separate variables when a temp
    is assigned to more than once.
    """

    fixture_category = "composing_methods/split_temporary_variable"

    def test_multiple_assignments(self):
        """Split a variable that's assigned multiple times."""
        self.refactor(
            "split-temporary-variable",
            target="calculate_distance::temp"
        )


class TestRemoveAssignmentsToParameters(RefactoringTestBase):
    """Test Remove Assignments to Parameters refactoring.

    Remove Assignments to Parameters uses a temporary variable
    instead of assigning to a parameter.
    """

    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_parameter_reassignment(self):
        """Remove assignments to parameters."""
        self.refactor(
            "remove-assignments-to-parameters",
            target="discount"
        )


class TestReplaceMethodWithMethodObject(RefactoringTestBase):
    """Test Replace Method with Method Object refactoring.

    Replace Method with Method Object turns a method into its own object
    so that local variables become fields on that object.
    """

    fixture_category = "composing_methods/replace_method_with_method_object"

    def test_complex_method(self):
        """Turn a complex method into a method object."""
        self.refactor(
            "replace-method-with-method-object",
            target="Account::gamma"
        )


class TestSubstituteAlgorithm(RefactoringTestBase):
    """Test Substitute Algorithm refactoring.

    Substitute Algorithm replaces an algorithm with one that is
    clearer or more efficient.
    """

    fixture_category = "composing_methods/substitute_algorithm"

    def test_replace_algorithm(self):
        """Replace algorithm with a clearer one."""
        self.refactor(
            "substitute-algorithm",
            target="found_person"
        )
