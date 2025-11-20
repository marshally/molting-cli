"""Tests for Rename refactoring.

This module tests the Rename refactoring which allows renaming
variables, methods, classes, or modules using rope's rename capability.
"""
from tests.conftest import RefactoringTestBase


class TestRenameFunction(RefactoringTestBase):
    """Tests for renaming functions."""
    fixture_category = "composing_methods/rename"

    def test_simple(self):
        """Rename a simple function."""
        self.refactor(
            "rename",
            target="add_numbers",
            new_name="calculate_sum"
        )


class TestRenameMethod(RefactoringTestBase):
    """Tests for renaming class methods."""
    fixture_category = "composing_methods/rename"

    def test_class_method(self):
        """Rename a class method."""
        self.refactor(
            "rename",
            target="Calculator::add_numbers",
            new_name="calculate_sum"
        )


class TestRenameClass(RefactoringTestBase):
    """Tests for renaming classes."""
    fixture_category = "composing_methods/rename"

    def test_rename_class_simple(self):
        """Rename a class."""
        self.refactor(
            "rename",
            target="Calculator",
            new_name="MathEngine"
        )


class TestRenameVariable(RefactoringTestBase):
    """Tests for renaming variables."""
    fixture_category = "composing_methods/rename"

    def test_rename_local_variable(self):
        """Rename a local variable."""
        self.refactor(
            "rename",
            target="count",
            new_name="total"
        )
