"""
Tests for Dealing with Generalization refactorings.

This module tests refactorings that manage inheritance hierarchies and relationships
between classes, including pulling up/pushing down fields and methods, extracting
superclasses and subclasses, collapsing hierarchies, and converting between
inheritance and delegation patterns.
"""

from tests.conftest import RefactoringTestBase


class TestPullUpField(RefactoringTestBase):
    """Tests for Pull Up Field refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_field"

    def test_simple(self):
        """Move a field from subclasses to the superclass."""
        self.refactor("pull-up-field", target="Salesman::name", to="Employee")


class TestPullUpMethod(RefactoringTestBase):
    """Tests for Pull Up Method refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_method"

    def test_simple(self):
        """Move identical methods from subclasses to the superclass."""
        self.refactor("pull-up-method", target="Salesman::get_annual_cost", to="Employee")


class TestPullUpConstructorBody(RefactoringTestBase):
    """Tests for Pull Up Constructor Body refactoring."""

    fixture_category = "dealing_with_generalization/pull_up_constructor_body"

    def test_simple(self):
        """Create a superclass constructor and call it from subclass constructors."""
        self.refactor("pull-up-constructor-body", target="Manager::__init__", to="Employee")


class TestPushDownMethod(RefactoringTestBase):
    """Tests for Push Down Method refactoring."""

    fixture_category = "dealing_with_generalization/push_down_method"

    def test_simple(self):
        """Move a method from superclass to those subclasses that need it."""
        self.refactor("push-down-method", target="Employee::get_quota", to="Salesman")


class TestPushDownField(RefactoringTestBase):
    """Tests for Push Down Field refactoring."""

    fixture_category = "dealing_with_generalization/push_down_field"

    def test_simple(self):
        """Move a field from superclass to those subclasses that need it."""
        self.refactor("push-down-field", target="Employee::quota", to="Salesman")


class TestExtractSubclass(RefactoringTestBase):
    """Tests for Extract Subclass refactoring."""

    fixture_category = "dealing_with_generalization/extract_subclass"

    def test_simple(self):
        """Create a subclass for a subset of features."""
        self.refactor(
            "extract-subclass", target="JobItem", features="is_labor,employee", name="LaborItem"
        )


class TestExtractSuperclass(RefactoringTestBase):
    """Tests for Extract Superclass refactoring."""

    fixture_category = "dealing_with_generalization/extract_superclass"

    def test_simple(self):
        """Create a superclass and move common features to it."""
        self.refactor("extract-superclass", targets="Employee,Department", name="Party")


class TestExtractInterface(RefactoringTestBase):
    """Tests for Extract Interface refactoring."""

    fixture_category = "dealing_with_generalization/extract_interface"

    def test_simple(self):
        """Create an interface for a common subset of methods."""
        self.refactor(
            "extract-interface",
            target="Employee",
            methods="get_rate,has_special_skill",
            name="Billable",
        )


class TestCollapseHierarchy(RefactoringTestBase):
    """Tests for Collapse Hierarchy refactoring."""

    fixture_category = "dealing_with_generalization/collapse_hierarchy"

    def test_simple(self):
        """Merge a subclass into its superclass."""
        self.refactor("collapse-hierarchy", target="Salesman", into="Employee")


class TestFormTemplateMethod(RefactoringTestBase):
    """Tests for Form Template Method refactoring."""

    fixture_category = "dealing_with_generalization/form_template_method"

    def test_simple(self):
        """Put the invariant parts of the algorithm in the superclass."""
        self.refactor(
            "form-template-method",
            targets="ResidentialSite::get_bill_amount,LifelineSite::get_bill_amount",
            name="get_bill_amount",
        )


class TestReplaceInheritanceWithDelegation(RefactoringTestBase):
    """Tests for Replace Inheritance with Delegation refactoring."""

    fixture_category = "dealing_with_generalization/replace_inheritance_with_delegation"

    def test_simple(self):
        """Create a field for the superclass and remove the subclassing."""
        self.refactor("replace-inheritance-with-delegation", target="Stack")


class TestReplaceDelegationWithInheritance(RefactoringTestBase):
    """Tests for Replace Delegation with Inheritance refactoring."""

    fixture_category = "dealing_with_generalization/replace_delegation_with_inheritance"

    def test_simple(self):
        """Make the delegating class a subclass of the delegate."""
        self.refactor("replace-delegation-with-inheritance", target="Employee", delegate="_person")
