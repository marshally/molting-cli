"""Tests for AST validators for different SymbolContext types."""

import libcst as cst
import pytest

from molting.core.ast_validators import (
    AttributeAccessValidator,
    MethodCallValidator,
    get_validator,
)
from molting.core.symbol_context import SymbolContext


class TestAttributeAccessValidator:
    """Tests for AttributeAccessValidator."""

    def test_matches_simple_attribute_access(self) -> None:
        """Test matching obj.field pattern."""
        code = "person.department"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value  # Get the expression

        validator = AttributeAccessValidator()
        assert validator.matches(expr, "department", on_object="person")

    def test_matches_chained_attribute_access(self) -> None:
        """Test matching obj.field1.field2 pattern."""
        code = "person.department.manager"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value

        validator = AttributeAccessValidator()
        # Should match the final attribute in the chain
        assert validator.matches(expr, "manager", on_object=None)

    def test_does_not_match_different_attribute(self) -> None:
        """Test that validator rejects different attribute names."""
        code = "person.name"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value

        validator = AttributeAccessValidator()
        assert not validator.matches(expr, "department", on_object="person")

    def test_does_not_match_method_call(self) -> None:
        """Test that validator rejects method calls."""
        code = "person.get_name()"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value

        validator = AttributeAccessValidator()
        # This is a Call node, not an Attribute node
        assert not validator.matches(expr, "get_name", on_object="person")


class TestMethodCallValidator:
    """Tests for MethodCallValidator."""

    def test_matches_simple_method_call(self) -> None:
        """Test matching obj.method() pattern."""
        code = "person.get_manager()"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value

        validator = MethodCallValidator()
        assert validator.matches(expr, "get_manager", on_object="person")

    def test_matches_method_call_with_args(self) -> None:
        """Test matching obj.method(args) pattern."""
        code = "calc.compute(10, 20)"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value

        validator = MethodCallValidator()
        assert validator.matches(expr, "compute", on_object="calc")

    def test_does_not_match_attribute_access(self) -> None:
        """Test that validator rejects plain attribute access."""
        code = "person.name"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value

        validator = MethodCallValidator()
        assert not validator.matches(expr, "name", on_object="person")

    def test_does_not_match_different_method(self) -> None:
        """Test that validator rejects different method names."""
        code = "person.get_name()"
        module = cst.parse_module(code)
        expr = module.body[0].body[0].value

        validator = MethodCallValidator()
        assert not validator.matches(expr, "get_manager", on_object="person")


class TestGetValidator:
    """Tests for the validator factory function."""

    def test_returns_attribute_access_validator(self) -> None:
        """Test getting AttributeAccessValidator."""
        validator = get_validator(SymbolContext.ATTRIBUTE_ACCESS)
        assert isinstance(validator, AttributeAccessValidator)

    def test_returns_method_call_validator(self) -> None:
        """Test getting MethodCallValidator."""
        validator = get_validator(SymbolContext.METHOD_CALL)
        assert isinstance(validator, MethodCallValidator)

    def test_raises_for_unsupported_context(self) -> None:
        """Test that unsupported contexts raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            get_validator(SymbolContext.IMPORT)
