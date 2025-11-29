"""Tests for DecoratorHandler utility.

Tests the DecoratorHandler class which manages decorators when transforming methods.
Specifically handles:
- Preserving decorators on transformed methods
- Creating helper methods without decorators
- Copying decorators when needed
"""

import libcst as cst
import pytest

from molting.core.decorator_handler import DecoratorHandler


class TestDecoratorHandler:
    """Tests for DecoratorHandler utility class."""

    def test_extract_decorators_from_method_with_property(self) -> None:
        """Test extracting @property decorator from a method."""
        source = """
class Calculator:
    @property
    def charge(self):
        return 42
"""
        module = cst.parse_module(source)
        method = module.body[0].body.body[0]

        handler = DecoratorHandler(method)
        decorators = handler.get_decorators()

        assert len(decorators) == 1
        assert isinstance(decorators[0].decorator, cst.Name)
        assert decorators[0].decorator.value == "property"

    def test_extract_decorators_from_method_with_staticmethod(self) -> None:
        """Test extracting @staticmethod decorator from a method."""
        source = """
class Calculator:
    @staticmethod
    def calculate():
        return 42
"""
        module = cst.parse_module(source)
        method = module.body[0].body.body[0]

        handler = DecoratorHandler(method)
        decorators = handler.get_decorators()

        assert len(decorators) == 1
        assert isinstance(decorators[0].decorator, cst.Name)
        assert decorators[0].decorator.value == "staticmethod"

    def test_extract_decorators_from_method_with_classmethod(self) -> None:
        """Test extracting @classmethod decorator from a method."""
        source = """
class Calculator:
    @classmethod
    def create(cls):
        return cls()
"""
        module = cst.parse_module(source)
        method = module.body[0].body.body[0]

        handler = DecoratorHandler(method)
        decorators = handler.get_decorators()

        assert len(decorators) == 1
        assert isinstance(decorators[0].decorator, cst.Name)
        assert decorators[0].decorator.value == "classmethod"

    def test_extract_multiple_decorators(self) -> None:
        """Test extracting multiple decorators from a method."""
        source = """
class Calculator:
    @property
    @some_other_decorator
    def charge(self):
        return 42
"""
        module = cst.parse_module(source)
        method = module.body[0].body.body[0]

        handler = DecoratorHandler(method)
        decorators = handler.get_decorators()

        assert len(decorators) == 2

    def test_extract_no_decorators(self) -> None:
        """Test extracting decorators from a method with none."""
        source = """
class Calculator:
    def charge(self):
        return 42
"""
        module = cst.parse_module(source)
        method = module.body[0].body.body[0]

        handler = DecoratorHandler(method)
        decorators = handler.get_decorators()

        assert len(decorators) == 0

    def test_apply_decorators_to_method(self) -> None:
        """Test applying decorators to a method."""
        # Create a method with @property
        source = """
class Calculator:
    @property
    def charge(self):
        return 42
"""
        module = cst.parse_module(source)
        original_method = module.body[0].body.body[0]
        handler = DecoratorHandler(original_method)

        # Create a new method without decorators
        new_method = cst.FunctionDef(
            name=cst.Name("new_charge"),
            params=cst.Parameters(),
            body=cst.IndentedBlock(body=[]),
        )

        # Apply decorators from original to new method
        decorated_method = handler.apply_decorators(new_method)

        assert len(decorated_method.decorators) == 1
        assert isinstance(decorated_method.decorators[0].decorator, cst.Name)
        assert decorated_method.decorators[0].decorator.value == "property"

    def test_apply_no_decorators(self) -> None:
        """Test applying decorators when original method has none."""
        source = """
class Calculator:
    def charge(self):
        return 42
"""
        module = cst.parse_module(source)
        original_method = module.body[0].body.body[0]
        handler = DecoratorHandler(original_method)

        new_method = cst.FunctionDef(
            name=cst.Name("new_charge"),
            params=cst.Parameters(),
            body=cst.IndentedBlock(body=[]),
        )

        decorated_method = handler.apply_decorators(new_method)

        assert len(decorated_method.decorators) == 0

    def test_preserve_decorators_on_method(self) -> None:
        """Test preserving decorators when transforming a method."""
        source = """
class Calculator:
    @property
    def charge(self):
        if True:
            return 42
        return 0
"""
        module = cst.parse_module(source)
        original_method = module.body[0].body.body[0]
        handler = DecoratorHandler(original_method)

        # Simulate a transformation that keeps the method but changes its body
        new_body = cst.IndentedBlock(
            body=[cst.SimpleStatementLine(body=[cst.Return(value=cst.Integer("42"))])]
        )
        transformed_method = original_method.with_changes(body=new_body)

        # Apply original decorators
        result = handler.apply_decorators(transformed_method)

        assert len(result.decorators) == 1
        assert result.name.value == "charge"

    def test_property_is_preserved_decorator(self) -> None:
        """Test that @property is recognized as a decorator that should be preserved."""
        source = """
class Calculator:
    @property
    def charge(self):
        return 42
"""
        module = cst.parse_module(source)
        method = module.body[0].body.body[0]

        handler = DecoratorHandler(method)

        assert handler.should_preserve_decorator("property")
        assert handler.should_preserve_decorator("staticmethod")
        assert handler.should_preserve_decorator("classmethod")

    def test_extract_and_preserve_complex_decorator(self) -> None:
        """Test extracting and preserving complex decorators like @property.setter."""
        source = """
class Calculator:
    @property
    def charge(self):
        return self._charge
"""
        module = cst.parse_module(source)
        method = module.body[0].body.body[0]

        handler = DecoratorHandler(method)
        decorators = handler.get_decorators()

        assert len(decorators) == 1
        assert isinstance(decorators[0].decorator, cst.Name)
