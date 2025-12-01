"""Tests for SymbolContext enum and related functionality."""


from molting.core.symbol_context import SymbolContext


class TestSymbolContext:
    """Tests for the SymbolContext enum."""

    def test_all_contexts_exist(self) -> None:
        """Test that all expected context types are defined."""
        # Core contexts
        assert SymbolContext.ATTRIBUTE_ACCESS.value == "attr"
        assert SymbolContext.METHOD_CALL.value == "call"
        assert SymbolContext.FUNCTION_CALL.value == "func"
        assert SymbolContext.ASSIGNMENT_TARGET.value == "assign"
        assert SymbolContext.PARAMETER.value == "param"
        assert SymbolContext.IMPORT.value == "import"

        # Additional contexts
        assert SymbolContext.TYPE_ANNOTATION.value == "type"
        assert SymbolContext.BASE_CLASS.value == "base"
        assert SymbolContext.DECORATOR.value == "decorator"
        assert SymbolContext.SUBSCRIPT.value == "subscript"
        assert SymbolContext.EXCEPTION_TYPE.value == "except"
        assert SymbolContext.WITH_TARGET.value == "with"
        assert SymbolContext.FOR_TARGET.value == "for"
        assert SymbolContext.COMPREHENSION_VAR.value == "comp"
        assert SymbolContext.DELETE_TARGET.value == "del"
        assert SymbolContext.AUGMENTED_ASSIGN.value == "aug"

    def test_context_count(self) -> None:
        """Test that we have all 16 expected contexts."""
        assert len(SymbolContext) == 16
