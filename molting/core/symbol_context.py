"""Symbol context types for identifying different usage patterns in code.

This module defines the SymbolContext enum which represents different ways a symbol
can be used in Python code. Each context type represents a specific AST pattern that
requires different matching and transformation logic.
"""

from enum import Enum


class SymbolContext(Enum):
    """Enumeration of different contexts where a symbol can appear in Python code.

    Each context represents a specific usage pattern that requires different AST
    matching logic when finding and updating references.
    """

    # Core contexts - most common usage patterns
    ATTRIBUTE_ACCESS = "attr"  # obj.field
    METHOD_CALL = "call"  # obj.method()
    FUNCTION_CALL = "func"  # function()
    ASSIGNMENT_TARGET = "assign"  # x = value
    PARAMETER = "param"  # def foo(x):
    IMPORT = "import"  # from x import y

    # Additional contexts - specialized usage patterns
    TYPE_ANNOTATION = "type"  # x: SomeType
    BASE_CLASS = "base"  # class Foo(Base):
    DECORATOR = "decorator"  # @decorator
    SUBSCRIPT = "subscript"  # obj[key]
    EXCEPTION_TYPE = "except"  # except Error:
    WITH_TARGET = "with"  # with ctx as x:
    FOR_TARGET = "for"  # for x in items:
    COMPREHENSION_VAR = "comp"  # [x for x in ...]
    DELETE_TARGET = "del"  # del obj.attr
    AUGMENTED_ASSIGN = "aug"  # x += 1
