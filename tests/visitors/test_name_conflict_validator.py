"""Tests for NameConflictValidator.

This module tests the NameConflictValidator which detects name conflicts
when creating new classes or constants at the module level.
"""

import pytest

from molting.core.name_conflict_validator import NameConflictValidator


class TestNameConflictValidator:
    """Tests for NameConflictValidator."""

    def test_detects_existing_class_conflict(self) -> None:
        """Test that validator detects when a class name already exists."""
        source_code = """\
class Customer:
    '''Existing class.'''

    def __init__(self, name):
        self.name = name
"""
        validator = NameConflictValidator(source_code)
        with pytest.raises(ValueError, match="Class.*Customer.*already exists"):
            validator.validate_class_name("Customer")

    def test_no_conflict_for_nonexistent_class(self) -> None:
        """Test that validator passes when class name doesn't exist."""
        source_code = """\
class Customer:
    '''Existing class.'''

    def __init__(self, name):
        self.name = name
"""
        validator = NameConflictValidator(source_code)
        # Should not raise
        validator.validate_class_name("Order")

    def test_detects_existing_constant_conflict(self) -> None:
        """Test that validator detects when a constant name already exists."""
        source_code = """\
GRAVITATIONAL_CONSTANT = 9.81


def potential_energy(mass, height):
    return mass * GRAVITATIONAL_CONSTANT * height
"""
        validator = NameConflictValidator(source_code)
        with pytest.raises(ValueError, match="Constant.*GRAVITATIONAL_CONSTANT.*already exists"):
            validator.validate_constant_name("GRAVITATIONAL_CONSTANT")

    def test_no_conflict_for_nonexistent_constant(self) -> None:
        """Test that validator passes when constant name doesn't exist."""
        source_code = """\
EXISTING_CONSTANT = 10


def my_function():
    pass
"""
        validator = NameConflictValidator(source_code)
        # Should not raise
        validator.validate_constant_name("NEW_CONSTANT")

    def test_detects_multiple_existing_classes(self) -> None:
        """Test validator with multiple classes in module."""
        source_code = """\
class Customer:
    pass


class Order:
    pass


class Invoice:
    pass
"""
        validator = NameConflictValidator(source_code)

        # Should detect all existing classes
        with pytest.raises(ValueError, match="Class.*Customer.*already exists"):
            validator.validate_class_name("Customer")

        with pytest.raises(ValueError, match="Class.*Order.*already exists"):
            validator.validate_class_name("Order")

        with pytest.raises(ValueError, match="Class.*Invoice.*already exists"):
            validator.validate_class_name("Invoice")

        # Should not conflict with non-existent class
        validator.validate_class_name("Payment")

    def test_ignores_class_names_in_functions(self) -> None:
        """Test that validator ignores class names defined inside functions."""
        source_code = """\
def create_class():
    class TemporaryClass:
        pass
    return TemporaryClass
"""
        validator = NameConflictValidator(source_code)
        # Should not raise - TemporaryClass is not at module level
        validator.validate_class_name("TemporaryClass")

    def test_ignores_class_names_in_nested_classes(self) -> None:
        """Test that validator ignores class names defined inside other classes."""
        source_code = """\
class Outer:
    class Inner:
        pass
"""
        validator = NameConflictValidator(source_code)
        # Should not raise - Inner is not at module level
        validator.validate_class_name("Inner")

    def test_ignores_constants_in_functions(self) -> None:
        """Test that validator ignores constants defined inside functions."""
        source_code = """\
def calculate():
    MAX_VALUE = 100
    return MAX_VALUE
"""
        validator = NameConflictValidator(source_code)
        # Should not raise - MAX_VALUE is not at module level
        validator.validate_constant_name("MAX_VALUE")

    def test_ignores_constants_in_classes(self) -> None:
        """Test that validator ignores constants defined inside classes."""
        source_code = """\
class MyClass:
    CONSTANT_VALUE = 42
"""
        validator = NameConflictValidator(source_code)
        # Should not raise - CONSTANT_VALUE is not at module level
        validator.validate_constant_name("CONSTANT_VALUE")

    def test_class_and_constant_different_namespaces(self) -> None:
        """Test that class and constant names don't conflict (different namespaces)."""
        source_code = """\
class Customer:
    pass


CUSTOMER = "customer"
"""
        validator = NameConflictValidator(source_code)

        # Both should detect their respective conflicts
        with pytest.raises(ValueError, match="Class.*Customer.*already exists"):
            validator.validate_class_name("Customer")

        with pytest.raises(ValueError, match="Constant.*CUSTOMER.*already exists"):
            validator.validate_constant_name("CUSTOMER")

        # But they shouldn't interfere with each other
        validator.validate_class_name("ORDER")
        validator.validate_constant_name("NewConstant")
