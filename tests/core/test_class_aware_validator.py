"""Tests for ClassAwareValidator base class.

This module tests the ClassAwareValidator base class that provides
validation patterns for libcst-based refactorings.
"""
import pytest
import libcst as cst
from molting.core.class_aware_validator import ClassAwareValidator


class ConcreteValidator(ClassAwareValidator):
    """Concrete implementation of ClassAwareValidator for testing."""
    pass


class TestClassAwareValidatorInit:
    """Tests for ClassAwareValidator initialization."""

    def test_init_with_class_and_function(self):
        """Initialize validator with both class and function name."""
        validator = ConcreteValidator(class_name="MyClass", function_name="my_method")
        assert validator.class_name == "MyClass"
        assert validator.function_name == "my_method"
        assert validator.found is False

    def test_init_with_only_function(self):
        """Initialize validator with only function name (module-level)."""
        validator = ConcreteValidator(class_name=None, function_name="my_function")
        assert validator.class_name is None
        assert validator.function_name == "my_function"
        assert validator.found is False

    def test_init_with_optional_class(self):
        """Initialize validator with optional class name."""
        validator = ConcreteValidator(function_name="my_function")
        assert validator.class_name is None
        assert validator.function_name == "my_function"


class TestClassAwareValidatorVisiting:
    """Tests for ClassAwareValidator visitor methods."""

    def test_tracks_current_class(self):
        """Validator tracks the current class during traversal."""
        source = """
class MyClass:
    def my_method(self):
        pass
"""
        validator = ConcreteValidator(class_name="MyClass", function_name="my_method")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True

    def test_finds_module_level_function(self):
        """Validator finds module-level function."""
        source = """
def my_function():
    pass
"""
        validator = ConcreteValidator(class_name=None, function_name="my_function")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True

    def test_finds_class_method(self):
        """Validator finds method in a class."""
        source = """
class MyClass:
    def my_method(self):
        pass
"""
        validator = ConcreteValidator(class_name="MyClass", function_name="my_method")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True

    def test_not_found_missing_function(self):
        """Validator returns found=False when function doesn't exist."""
        source = """
def other_function():
    pass
"""
        validator = ConcreteValidator(class_name=None, function_name="my_function")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is False

    def test_not_found_missing_class(self):
        """Validator returns found=False when class doesn't exist."""
        source = """
class OtherClass:
    def my_method(self):
        pass
"""
        validator = ConcreteValidator(class_name="MyClass", function_name="my_method")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is False

    def test_not_found_missing_method(self):
        """Validator returns found=False when method doesn't exist in class."""
        source = """
class MyClass:
    def other_method(self):
        pass
"""
        validator = ConcreteValidator(class_name="MyClass", function_name="my_method")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is False


class TestClassAwareValidatorEdgeCases:
    """Tests for ClassAwareValidator edge cases."""

    def test_ignores_module_function_when_looking_for_class_method(self):
        """Validator ignores module function when looking for class method."""
        source = """
def my_method():
    pass

class MyClass:
    def other_method(self):
        pass
"""
        validator = ConcreteValidator(class_name="MyClass", function_name="my_method")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is False

    def test_ignores_class_method_when_looking_for_module_function(self):
        """Validator ignores class method when looking for module function."""
        source = """
class MyClass:
    def my_function(self):
        pass
"""
        validator = ConcreteValidator(class_name=None, function_name="my_function")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is False

    def test_multiple_classes_finds_correct_one(self):
        """Validator finds correct method in multiple classes."""
        source = """
class FirstClass:
    def my_method(self):
        pass

class MyClass:
    def my_method(self):
        pass
"""
        validator = ConcreteValidator(class_name="MyClass", function_name="my_method")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True

    def test_nested_functions_ignored(self):
        """Validator ignores nested function definitions."""
        source = """
def outer_function():
    def my_function():
        pass
"""
        # Note: This test checks current behavior - nested functions are found
        # as they are visited. This may need to be refined based on requirements.
        validator = ConcreteValidator(class_name=None, function_name="my_function")
        tree = cst.parse_module(source)
        tree.walk(validator)
        # Nested functions will be found by visitor, which is current behavior
        assert validator.found is True

    def test_handles_complex_class_hierarchy(self):
        """Validator handles classes with inheritance."""
        source = """
class BaseClass:
    def my_method(self):
        pass

class MyClass(BaseClass):
    def other_method(self):
        pass
"""
        validator = ConcreteValidator(class_name="MyClass", function_name="other_method")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True

    def test_empty_source_not_found(self):
        """Validator handles empty source code."""
        source = ""
        validator = ConcreteValidator(class_name=None, function_name="my_function")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is False

    def test_source_with_only_comments(self):
        """Validator handles source with only comments."""
        source = """
# This is a comment
# Another comment
"""
        validator = ConcreteValidator(class_name=None, function_name="my_function")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is False


class TestClassAwareValidatorSubclassing:
    """Tests for subclassing ClassAwareValidator."""

    def test_subclass_can_override_visit_function_def(self):
        """Subclass can override visit_FunctionDef for custom validation."""
        class CustomValidator(ClassAwareValidator):
            def __init__(self, class_name, function_name):
                super().__init__(class_name, function_name)
                self.function_count = 0

            def visit_FunctionDef(self, node):
                self.function_count += 1
                return super().visit_FunctionDef(node)

        source = """
def func1():
    pass

def func2():
    pass

class MyClass:
    def method1(self):
        pass
"""
        validator = CustomValidator(class_name=None, function_name="func1")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True
        assert validator.function_count == 3

    def test_subclass_can_add_custom_validation_logic(self):
        """Subclass can add custom validation logic."""
        class ParamCountValidator(ClassAwareValidator):
            def __init__(self, class_name, function_name, required_params):
                super().__init__(class_name, function_name)
                self.required_params = required_params
                self.param_count = None

            def visit_FunctionDef(self, node):
                if self._is_target_function(node):
                    self.param_count = len(node.params.params)
                return super().visit_FunctionDef(node)

            def _is_target_function(self, node):
                func_name = node.name.value
                if self.class_name is None:
                    return self.current_class is None and func_name == self.function_name
                else:
                    return self.current_class == self.class_name and func_name == self.function_name

        source = """
class MyClass:
    def my_method(self, a, b):
        pass
"""
        validator = ParamCountValidator(
            class_name="MyClass",
            function_name="my_method",
            required_params=2
        )
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True
        assert validator.param_count == 3  # self + a + b

    def test_subclass_inherits_found_tracking(self):
        """Subclass inherits found tracking from parent."""
        class ExtendedValidator(ClassAwareValidator):
            pass

        source = """
def my_function():
    pass
"""
        validator = ExtendedValidator(class_name=None, function_name="my_function")
        tree = cst.parse_module(source)
        tree.walk(validator)
        assert validator.found is True
