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

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test extract method with local variables."""
        # Extract calculation that uses and modifies local variable 'outstanding'
        self.refactor(
            "extract-method",
            target="Order::print_owing#L18-L19",
            name="calculate_outstanding",
        )

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test extract method with instance variables."""
        # Extract subtotal calculation that uses self.items
        self.refactor(
            "extract-method",
            target="Order::calculate_total#L13-L15",
            name="calculate_subtotal",
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test extract method when target method name already exists."""
        # Try to extract to print_banner but it already exists
        self.refactor("extract-method", target="Order::print_owing#L13-L15", name="print_banner")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test extract method with decorated methods."""
        # Extract pricing calculation from @property decorated method
        self.refactor(
            "extract-method",
            target="Product::display_info#L23-L25",
            name="_calculate_pricing",
        )


class TestExtractFunction(RefactoringTestBase):
    """Tests for Extract Function refactoring."""

    fixture_category = "composing_methods/extract_function"

    def test_simple(self) -> None:
        """Extract code into a module-level function."""
        self.refactor(
            "extract-function", target="DataProcessor::process#L4", name="normalize_string"
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test extract function when target function name already exists."""
        # Try to extract to normalize_string but it already exists at module level
        self.refactor(
            "extract-function", target="DataProcessor::process#L12", name="normalize_string"
        )

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test extract function from decorated methods."""
        # Extract email formatting from @log_call decorated method
        self.refactor(
            "extract-function",
            target="EmailService::send_email#L19",
            name="format_email_address",
        )


class TestInlineMethod(RefactoringTestBase):
    """Tests for Inline Method refactoring."""

    fixture_category = "composing_methods/inline_method"

    def test_simple(self) -> None:
        """Inline a simple method whose body is as clear as its name."""
        self.refactor("inline-method", target="Person::more_than_five_late_deliveries")

    @pytest.mark.skip(reason="Implementation needed for with_instance_vars")
    def test_with_instance_vars(self) -> None:
        """Test inline method with instance variables."""
        # Inline get_subtotal which uses self.items
        self.refactor("inline-method", target="ShoppingCart::get_subtotal")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test inline method with decorated methods."""
        # Inline _get_base_total into the @property decorated total method
        self.refactor("inline-method", target="ShoppingCart::_get_base_total")

    def test_multiple_calls(self) -> None:
        """Test inline method with multiple call sites."""
        self.refactor("inline-method", target="Person::more_than_five_late_deliveries")


class TestInlineTemp(RefactoringTestBase):
    """Tests for Inline Temp refactoring."""

    fixture_category = "composing_methods/inline_temp"

    def test_simple(self) -> None:
        """Replace a temp variable with its expression."""
        self.refactor("inline-temp", target="calculate_total::base_price")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test inline temp with local variables used in multiple places."""
        self.refactor("inline-temp", target="calculate_price::base_price")


class TestReplaceTempWithQuery(RefactoringTestBase):
    """Tests for Replace Temp with Query refactoring."""

    fixture_category = "composing_methods/replace_temp_with_query"

    def test_simple(self) -> None:
        """Extract expression into a method and replace temp."""
        self.refactor("replace-temp-with-query", target="Order::get_price::base_price")

    @pytest.mark.skip(reason="Implementation needed for with_locals")
    def test_with_locals(self) -> None:
        """Test replace temp with query with local variables used multiple times."""
        self.refactor("replace-temp-with-query", target="Invoice::calculate_total::base_price")

    def test_with_instance_vars(self) -> None:
        """Test replace temp with query with instance variables."""
        # Replace discounted_price temp with a query method that uses instance vars
        self.refactor(
            "replace-temp-with-query", target="Product::get_final_price::discounted_price"
        )

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test replace temp with query when method name already exists."""
        # Try to replace base_price temp with a method but the method already exists
        self.refactor("replace-temp-with-query", target="Order::get_price::base_price")

    @pytest.mark.skip(reason="Implementation needed for with_decorators")
    def test_with_decorators(self) -> None:
        """Test replace temp with query with decorated methods."""
        # Replace perimeter temp in @property decorated area method
        self.refactor("replace-temp-with-query", target="Rectangle::area::perimeter")


class TestIntroduceExplainingVariable(RefactoringTestBase):
    """Tests for Introduce Explaining Variable refactoring."""

    fixture_category = "composing_methods/introduce_explaining_variable"

    def test_simple(self) -> None:
        """Put complex expressions into named temp variables."""
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard

        # Apply all three refactorings before checking
        # Note: Line numbers shift as variables are introduced
        # Original: L3=base_price expr, L4=quantity_discount expr, L5=shipping expr
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L3",
            name="base_price",
        )
        # After first: L5=quantity_discount expr (shifted due to new assignment)
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L5",
            name="quantity_discount",
        )
        # After second: L7=shipping expr (min(...) is on line 7)
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L7",
            name="shipping",
        )
        self.assert_matches_expected()

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test introduce explaining variable when variable name already exists."""
        # Try to introduce base_price but it already exists
        self.refactor(
            "introduce-explaining-variable",
            target="calculate_total#L7",
            name="base_price",
        )


class TestIntroduceExplainingVariableReplaceAll(RefactoringTestBase):
    """Tests for Introduce Explaining Variable with replace_all option."""

    fixture_category = "composing_methods/introduce_explaining_variable/replace_all"

    def test_simple(self) -> None:
        """Extract expression and replace all occurrences with the variable.

        This tests the more advanced version of introduce-explaining-variable
        that also replaces other occurrences of the extracted expression with
        the new variable name. For example, extracting `order.quantity * order.item_price`
        to `base_price` should also replace `order.quantity * order.item_price` in
        the min() call with `base_price`.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard

        # Apply refactorings with replace_all=True
        # Note: Line numbers shift as variables are introduced
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L3",
            name="base_price",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L5",
            name="quantity_discount",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            target="calculate_total#L7",
            name="shipping",
            replace_all=True,
        )
        self.assert_matches_expected()

    def test_condensed(self) -> None:
        """Extract expressions using expression-based targeting (not line numbers).

        This tests the expression-based targeting mode using --in_function and
        --expression parameters. This is useful when expressions span multiple
        lines or don't have clean line boundaries.
        """
        from molting.cli import refactor_file

        assert self.test_file is not None  # Type guard

        # Use expression-based targeting - no need to track line numbers!
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            in_function="calculate_total",
            expression="order.quantity * order.item_price",
            name="base_price",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            in_function="calculate_total",
            expression="max(0, order.quantity - 500) * order.item_price * 0.05",
            name="quantity_discount",
            replace_all=True,
        )
        refactor_file(
            "introduce-explaining-variable",
            self.test_file,
            in_function="calculate_total",
            expression="min(base_price * 0.1, 100.0)",
            name="shipping",
            replace_all=True,
        )
        self.assert_matches_expected()


class TestSplitTemporaryVariable(RefactoringTestBase):
    """Tests for Split Temporary Variable refactoring."""

    fixture_category = "composing_methods/split_temporary_variable"

    def test_simple(self) -> None:
        """Split a temp variable assigned multiple times."""
        self.refactor("split-temporary-variable", target="calculate_distance::temp")

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test split temporary variable when new variable name already exists."""
        # Try to split temp to primary_acc but it already exists
        self.refactor("split-temporary-variable", target="calculate_distance::temp")


class TestRemoveAssignmentsToParameters(RefactoringTestBase):
    """Tests for Remove Assignments to Parameters refactoring."""

    fixture_category = "composing_methods/remove_assignments_to_parameters"

    def test_simple(self) -> None:
        """Use a temp variable instead of assigning to parameters."""
        self.refactor("remove-assignments-to-parameters", target="discount")


class TestReplaceMethodWithMethodObject(RefactoringTestBase):
    """Tests for Replace Method with Method Object refactoring."""

    fixture_category = "composing_methods/replace_method_with_method_object"

    def test_simple(self) -> None:
        """Turn a long method into its own object."""
        self.refactor("replace-method-with-method-object", target="Account::gamma")

    def test_with_instance_vars(self) -> None:
        """Test replace method with method object with instance variables."""
        # Convert method that uses multiple instance vars to method object
        self.refactor("replace-method-with-method-object", target="Order::calculate_total")

    @pytest.mark.skip(reason="Implementation needed for name_conflict")
    def test_name_conflict(self) -> None:
        """Test replace method with method object when class name already exists."""
        # Try to create Gamma class but it already exists
        self.refactor("replace-method-with-method-object", target="Account::gamma")

    def test_with_decorators(self) -> None:
        """Test replace method with method object with decorated methods."""
        # Convert @log_call decorated method to method object
        self.refactor("replace-method-with-method-object", target="Report::generate_summary")


class TestSubstituteAlgorithm(RefactoringTestBase):
    """Tests for Substitute Algorithm refactoring."""

    fixture_category = "composing_methods/substitute_algorithm"

    def test_simple(self) -> None:
        """Replace an algorithm with a clearer one."""
        self.refactor("substitute-algorithm", target="found_person")
