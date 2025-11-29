"""
Tests for Pull Up Constructor Body refactoring.

This refactoring extracts common constructor initialization code from subclasses
and moves it to the superclass constructor.
"""


from tests.conftest import RefactoringTestBase


class TestPullUpConstructorBody(RefactoringTestBase):
    """Tests for Pull Up Constructor Body refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_constructor_body"

    def test_simple(self) -> None:
        """Test basic extraction of common constructor initialization code.

        Creates a superclass constructor for Employee and extracts the common
        initialization logic from Manager's constructor, with Manager calling
        the superclass constructor. This is the simplest case with straightforward
        initialization code that can be directly moved to the parent.
        """
        self.refactor("pull-up-constructor-body", target="Manager::__init__", to="Employee")

    def test_with_locals(self) -> None:
        """Test pull-up-constructor-body when constructor uses local variables.

        Unlike test_simple, this tests extracting constructor code that declares
        and uses local variables. The refactoring must properly handle these
        locals: either converting them to instance variables or managing their
        scope across the extracted superclass constructor call.
        """
        self.refactor("pull-up-constructor-body", target="Manager::__init__", to="Employee")

    def test_name_conflict(self) -> None:
        """Test pull-up-constructor-body when parent already has a different constructor.

        Unlike test_simple, this tests the case where Employee already has its own
        __init__ method that is incompatible with the code being extracted from
        Manager. The refactoring must either merge the constructors intelligently
        or raise a clear error about the incompatibility.
        """
        self.refactor("pull-up-constructor-body", target="Manager::__init__", to="Employee")
