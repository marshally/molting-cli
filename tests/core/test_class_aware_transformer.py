"""
Tests for ClassAwareTransformer base class.

This module tests the ClassAwareTransformer base class that provides
class/method context tracking for libcst transformers.
"""
import pytest
import libcst as cst
from typing import Optional

from molting.core.class_aware_transformer import ClassAwareTransformer


class SimpleTransformer(ClassAwareTransformer):
    """A simple transformer for testing purposes."""

    def __init__(self, class_name: Optional[str], function_name: str):
        """Initialize the transformer with target class and function names."""
        super().__init__(class_name=class_name, function_name=function_name)
        self.visited_functions = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Track which functions were visited."""
        func_name = original_node.name.value
        self.visited_functions.append(
            {"name": func_name, "class": self.current_class}
        )

        # Record if this matches the target
        if self.matches_target():
            self.visited_functions[-1]["matched"] = True

        return updated_node


class TestClassAwareTransformer:
    """Tests for ClassAwareTransformer functionality."""

    def test_tracks_module_level_function(self):
        """Test that transformer tracks module-level functions."""
        source = "def foo():\n    pass\n"
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name=None, function_name="foo")
        tree.visit(transformer)

        assert len(transformer.visited_functions) == 1
        assert transformer.visited_functions[0]["name"] == "foo"
        assert transformer.visited_functions[0]["class"] is None

    def test_matches_module_level_function(self):
        """Test that transformer correctly matches module-level functions."""
        source = "def foo():\n    pass\n"
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name=None, function_name="foo")
        tree.visit(transformer)

        assert transformer.visited_functions[0].get("matched") is True

    def test_does_not_match_different_module_level_function(self):
        """Test that transformer doesn't match different functions."""
        source = "def foo():\n    pass\ndef bar():\n    pass\n"
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name=None, function_name="foo")
        tree.visit(transformer)

        assert len(transformer.visited_functions) == 2
        assert transformer.visited_functions[0].get("matched") is True
        assert transformer.visited_functions[1].get("matched") is None

    def test_tracks_class_context(self):
        """Test that transformer tracks current class context."""
        source = """
class MyClass:
    def method(self):
        pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="MyClass", function_name="method")
        tree.visit(transformer)

        assert len(transformer.visited_functions) == 1
        assert transformer.visited_functions[0]["name"] == "method"
        assert transformer.visited_functions[0]["class"] == "MyClass"

    def test_matches_class_method(self):
        """Test that transformer matches methods in target class."""
        source = """
class MyClass:
    def method(self):
        pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="MyClass", function_name="method")
        tree.visit(transformer)

        assert transformer.visited_functions[0].get("matched") is True

    def test_does_not_match_method_in_different_class(self):
        """Test that transformer doesn't match methods in other classes."""
        source = """
class MyClass:
    def method(self):
        pass

class OtherClass:
    def method(self):
        pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="MyClass", function_name="method")
        tree.visit(transformer)

        assert len(transformer.visited_functions) == 2
        assert transformer.visited_functions[0].get("matched") is True
        assert transformer.visited_functions[1].get("matched") is None

    def test_does_not_match_different_method_in_class(self):
        """Test that transformer doesn't match different methods in target class."""
        source = """
class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="MyClass", function_name="method1")
        tree.visit(transformer)

        assert len(transformer.visited_functions) == 2
        assert transformer.visited_functions[0].get("matched") is True
        assert transformer.visited_functions[1].get("matched") is None

    def test_resets_current_class_on_leave(self):
        """Test that current_class is reset when leaving a class."""
        source = """
class MyClass:
    def method(self):
        pass

def module_func():
    pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name=None, function_name="module_func")
        tree.visit(transformer)

        # The module-level function should have current_class = None
        module_func = [f for f in transformer.visited_functions if f["name"] == "module_func"][0]
        assert module_func["class"] is None

    def test_handles_nested_classes(self):
        """Test behavior with nested classes."""
        source = """
class OuterClass:
    def outer_method(self):
        pass

    class InnerClass:
        def inner_method(self):
            pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="OuterClass", function_name="outer_method")
        tree.visit(transformer)

        # Find the outer method
        outer = [f for f in transformer.visited_functions if f["name"] == "outer_method"]
        assert len(outer) == 1
        assert outer[0].get("matched") is True

    def test_current_class_attribute_accessible(self):
        """Test that current_class attribute is accessible and correctly maintained."""
        source = """
class TestClass:
    def test_method(self):
        pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="TestClass", function_name="test_method")

        # Before traversal
        assert transformer.current_class is None

        tree.visit(transformer)

        # After traversal (should be reset)
        assert transformer.current_class is None

    def test_matches_target_returns_bool(self):
        """Test that matches_target returns a boolean."""
        source = "def foo():\n    pass\n"
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name=None, function_name="foo")
        tree.visit(transformer)

        # Call matches_target directly in a leaf context
        # We can't easily test during traversal, so we test the logic
        transformer2 = SimpleTransformer(class_name=None, function_name="foo")
        transformer2.current_class = None
        assert isinstance(transformer2.matches_target(), bool)

    def test_module_level_with_class_name_does_not_match(self):
        """Test that module-level function doesn't match when class_name is specified."""
        source = "def foo():\n    pass\n"
        tree = cst.parse_module(source)
        # Looking for a class method but traversing module-level function
        transformer = SimpleTransformer(class_name="SomeClass", function_name="foo")
        tree.visit(transformer)

        # Should not match because we're looking for a class method
        assert transformer.visited_functions[0].get("matched") is None

    def test_multiple_classes_with_same_method_name(self):
        """Test handling of same method names in different classes."""
        source = """
class ClassA:
    def same_method(self):
        pass

class ClassB:
    def same_method(self):
        pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="ClassA", function_name="same_method")
        tree.visit(transformer)

        assert len(transformer.visited_functions) == 2
        # Only ClassA's same_method should match
        class_a_match = [f for f in transformer.visited_functions if f["class"] == "ClassA"][0]
        class_b_match = [f for f in transformer.visited_functions if f["class"] == "ClassB"][0]

        assert class_a_match.get("matched") is True
        assert class_b_match.get("matched") is None

    def test_inheritance_does_not_affect_matching(self):
        """Test that class inheritance doesn't affect matching logic."""
        source = """
class Parent:
    def parent_method(self):
        pass

class Child(Parent):
    def child_method(self):
        pass
"""
        tree = cst.parse_module(source)
        transformer = SimpleTransformer(class_name="Child", function_name="parent_method")
        tree.visit(transformer)

        # Looking for parent_method in Child, but it's defined in Parent
        # Should not match (matching is based on definition location, not inheritance)
        parent_method = [f for f in transformer.visited_functions if f["name"] == "parent_method"][0]
        assert parent_method["class"] == "Parent"
        assert parent_method.get("matched") is None
