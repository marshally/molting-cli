"""
Tests for AST utility functions.

This module tests the core AST utility functions used across refactorings,
including field extraction from __init__ methods.
"""

import libcst as cst

from molting.core.ast_utils import (
    extract_all_methods,
    extract_init_field_assignments,
    find_class_in_module,
    find_method_in_class,
    find_self_field_assignment,
    is_assignment_to_field,
    parse_comma_separated_list,
)


class TestExtractInitFieldAssignments:
    """Tests for extract_init_field_assignments() function."""

    def test_simple_init_with_fields(self) -> None:
        """Should extract all self.field = value assignments."""
        code = """
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)
        init_method = class_def.body.body[0]
        assert isinstance(init_method, cst.FunctionDef)

        fields = extract_init_field_assignments(init_method)

        assert len(fields) == 2
        assert "name" in fields
        assert "age" in fields

    def test_init_with_no_fields(self) -> None:
        """Should return empty dict when no fields are assigned."""
        code = """
class Empty:
    def __init__(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)
        init_method = class_def.body.body[0]
        assert isinstance(init_method, cst.FunctionDef)

        fields = extract_init_field_assignments(init_method)

        assert len(fields) == 0
        assert fields == {}

    def test_init_with_mixed_statements(self) -> None:
        """Should extract only self.field assignments, ignoring other statements."""
        code = """
class Person:
    def __init__(self, name, age):
        self.name = name
        local_var = "hello"
        self.age = age
        print("initialized")
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)
        init_method = class_def.body.body[0]
        assert isinstance(init_method, cst.FunctionDef)

        fields = extract_init_field_assignments(init_method)

        assert len(fields) == 2
        assert "name" in fields
        assert "age" in fields

    def test_init_with_complex_values(self) -> None:
        """Should extract fields with complex assigned values."""
        code = """
class Person:
    def __init__(self, name):
        self.name = name.strip().upper()
        self.created_at = datetime.now()
        self.count = 0
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)
        init_method = class_def.body.body[0]
        assert isinstance(init_method, cst.FunctionDef)

        fields = extract_init_field_assignments(init_method)

        assert len(fields) == 3
        assert "name" in fields
        assert "created_at" in fields
        assert "count" in fields

    def test_init_with_private_fields(self) -> None:
        """Should extract fields with underscore prefixes."""
        code = """
class Person:
    def __init__(self, name):
        self._name = name
        self.__secret = "hidden"
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)
        init_method = class_def.body.body[0]
        assert isinstance(init_method, cst.FunctionDef)

        fields = extract_init_field_assignments(init_method)

        assert len(fields) == 2
        assert "_name" in fields
        assert "__secret" in fields

    def test_init_with_multiple_targets(self) -> None:
        """Should handle assignments to multiple targets (last target wins)."""
        code = """
class Person:
    def __init__(self, name):
        self.name = self.full_name = name
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)
        init_method = class_def.body.body[0]
        assert isinstance(init_method, cst.FunctionDef)

        fields = extract_init_field_assignments(init_method)

        # Should capture both assignments
        assert len(fields) >= 1
        assert "name" in fields or "full_name" in fields


class TestFindSelfFieldAssignment:
    """Tests for find_self_field_assignment() function."""

    def test_simple_self_assignment(self) -> None:
        """Should return (field_name, value) for self.field = value."""
        code = "self.name = name"
        module = cst.parse_module(code)
        stmt = module.body[0]
        assert isinstance(stmt, cst.SimpleStatementLine)

        result = find_self_field_assignment(stmt)

        assert result is not None
        field_name, value = result
        assert field_name == "name"
        assert isinstance(value, cst.Name)
        assert value.value == "name"

    def test_non_self_assignment(self) -> None:
        """Should return None for assignments not to self."""
        code = "local_var = value"
        module = cst.parse_module(code)
        stmt = module.body[0]
        assert isinstance(stmt, cst.SimpleStatementLine)

        result = find_self_field_assignment(stmt)

        assert result is None

    def test_other_object_assignment(self) -> None:
        """Should return None for assignments to other objects."""
        code = "obj.field = value"
        module = cst.parse_module(code)
        stmt = module.body[0]
        assert isinstance(stmt, cst.SimpleStatementLine)

        result = find_self_field_assignment(stmt)

        assert result is None

    def test_complex_value(self) -> None:
        """Should handle complex values."""
        code = "self.name = first.strip().upper()"
        module = cst.parse_module(code)
        stmt = module.body[0]
        assert isinstance(stmt, cst.SimpleStatementLine)

        result = find_self_field_assignment(stmt)

        assert result is not None
        field_name, value = result
        assert field_name == "name"
        assert isinstance(value, cst.Call)

    def test_private_field(self) -> None:
        """Should handle private fields."""
        code = "self._private = value"
        module = cst.parse_module(code)
        stmt = module.body[0]
        assert isinstance(stmt, cst.SimpleStatementLine)

        result = find_self_field_assignment(stmt)

        assert result is not None
        field_name, value = result
        assert field_name == "_private"

    def test_non_statement_line(self) -> None:
        """Should return None for non-SimpleStatementLine."""
        code = """
if True:
    pass
"""
        module = cst.parse_module(code)
        stmt = module.body[0]
        # This is an If statement, not a SimpleStatementLine
        assert isinstance(stmt, cst.If)

        # Pass the statement directly (not a SimpleStatementLine)
        result = find_self_field_assignment(stmt)  # type: ignore

        assert result is None

    def test_non_assignment_statement(self) -> None:
        """Should return None for non-assignment statements."""
        code = "print('hello')"
        module = cst.parse_module(code)
        stmt = module.body[0]
        assert isinstance(stmt, cst.SimpleStatementLine)

        result = find_self_field_assignment(stmt)

        assert result is None


class TestIsAssignmentToField:
    """Tests for is_assignment_to_field() function."""

    def test_assignment_to_tracked_field(self) -> None:
        """Should return True for assignment to a field in the set."""
        code = "self.name = value"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"name", "age"})

        assert result is True

    def test_assignment_to_untracked_field(self) -> None:
        """Should return False for assignment to field not in set."""
        code = "self.name = value"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"age", "phone"})

        assert result is False

    def test_non_self_assignment(self) -> None:
        """Should return False for non-self assignments."""
        code = "local_var = value"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"name"})

        assert result is False

    def test_empty_field_set(self) -> None:
        """Should return False when field set is empty."""
        code = "self.name = value"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, set())

        assert result is False

    def test_multiple_fields(self) -> None:
        """Should return True if any field in set matches."""
        code = "self.phone = value"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"name", "age", "phone", "email"})

        assert result is True

    def test_private_field_in_set(self) -> None:
        """Should handle private fields."""
        code = "self._private = value"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"_private", "public"})

        assert result is True

    def test_non_assignment_statement(self) -> None:
        """Should return False for non-assignment statements."""
        code = "print('hello')"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"name"})

        assert result is False

    def test_if_statement(self) -> None:
        """Should return False for if statements."""
        code = """
if True:
    pass
"""
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"name"})

        assert result is False

    def test_assignment_to_other_object(self) -> None:
        """Should return False for assignments to other objects."""
        code = "obj.name = value"
        module = cst.parse_module(code)
        stmt = module.body[0]

        result = is_assignment_to_field(stmt, {"name"})

        assert result is False


class TestFindClassInModule:
    """Tests for find_class_in_module() function."""

    def test_find_existing_class(self) -> None:
        """Should find a class by name in module."""
        code = """
class Person:
    pass

class Animal:
    pass
"""
        module = cst.parse_module(code)

        result = find_class_in_module(module, "Person")

        assert result is not None
        assert isinstance(result, cst.ClassDef)
        assert result.name.value == "Person"

    def test_find_second_class(self) -> None:
        """Should find second class in module."""
        code = """
class Person:
    pass

class Animal:
    pass
"""
        module = cst.parse_module(code)

        result = find_class_in_module(module, "Animal")

        assert result is not None
        assert isinstance(result, cst.ClassDef)
        assert result.name.value == "Animal"

    def test_class_not_found(self) -> None:
        """Should return None when class doesn't exist."""
        code = """
class Person:
    pass
"""
        module = cst.parse_module(code)

        result = find_class_in_module(module, "NotFound")

        assert result is None

    def test_empty_module(self) -> None:
        """Should return None for empty module."""
        code = ""
        module = cst.parse_module(code)

        result = find_class_in_module(module, "Person")

        assert result is None

    def test_module_with_functions_only(self) -> None:
        """Should return None when module has no classes."""
        code = """
def function1():
    pass

def function2():
    pass
"""
        module = cst.parse_module(code)

        result = find_class_in_module(module, "Person")

        assert result is None


class TestFindMethodInClass:
    """Tests for find_method_in_class() function."""

    def test_find_existing_method(self) -> None:
        """Should find a method by name in class."""
        code = """
class Person:
    def greet(self):
        pass

    def farewell(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        result = find_method_in_class(class_def, "greet")

        assert result is not None
        assert isinstance(result, cst.FunctionDef)
        assert result.name.value == "greet"

    def test_find_init_method(self) -> None:
        """Should find __init__ method."""
        code = """
class Person:
    def __init__(self):
        pass

    def greet(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        result = find_method_in_class(class_def, "__init__")

        assert result is not None
        assert isinstance(result, cst.FunctionDef)
        assert result.name.value == "__init__"

    def test_method_not_found(self) -> None:
        """Should return None when method doesn't exist."""
        code = """
class Person:
    def greet(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        result = find_method_in_class(class_def, "not_found")

        assert result is None

    def test_empty_class(self) -> None:
        """Should return None for empty class."""
        code = """
class Empty:
    pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        result = find_method_in_class(class_def, "method")

        assert result is None

    def test_class_with_fields_only(self) -> None:
        """Should return None when class has no methods."""
        code = """
class Person:
    name: str
    age: int
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        result = find_method_in_class(class_def, "method")

        assert result is None


class TestExtractAllMethods:
    """Tests for extract_all_methods() function."""

    def test_extract_multiple_methods(self) -> None:
        """Should extract all methods from class."""
        code = """
class Person:
    def __init__(self):
        pass

    def greet(self):
        pass

    def farewell(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        methods = extract_all_methods(class_def)

        assert len(methods) == 3
        assert all(isinstance(m, cst.FunctionDef) for m in methods)
        method_names = [m.name.value for m in methods]
        assert "__init__" in method_names
        assert "greet" in method_names
        assert "farewell" in method_names

    def test_exclude_init(self) -> None:
        """Should exclude __init__ when requested."""
        code = """
class Person:
    def __init__(self):
        pass

    def greet(self):
        pass

    def farewell(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        methods = extract_all_methods(class_def, exclude_init=True)

        assert len(methods) == 2
        method_names = [m.name.value for m in methods]
        assert "__init__" not in method_names
        assert "greet" in method_names
        assert "farewell" in method_names

    def test_empty_class(self) -> None:
        """Should return empty list for empty class."""
        code = """
class Empty:
    pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        methods = extract_all_methods(class_def)

        assert methods == []

    def test_class_with_fields_only(self) -> None:
        """Should return empty list when class has no methods."""
        code = """
class Person:
    name: str
    age: int
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        methods = extract_all_methods(class_def)

        assert methods == []

    def test_single_method(self) -> None:
        """Should handle class with single method."""
        code = """
class Person:
    def greet(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        methods = extract_all_methods(class_def)

        assert len(methods) == 1
        assert methods[0].name.value == "greet"

    def test_exclude_init_no_init_present(self) -> None:
        """Should handle exclude_init when no __init__ exists."""
        code = """
class Person:
    def greet(self):
        pass
"""
        module = cst.parse_module(code)
        class_def = module.body[0]
        assert isinstance(class_def, cst.ClassDef)

        methods = extract_all_methods(class_def, exclude_init=True)

        assert len(methods) == 1
        assert methods[0].name.value == "greet"


class TestParseCommaSeparatedList:
    """Tests for parse_comma_separated_list() function."""

    def test_simple_list(self) -> None:
        """Should parse simple comma-separated list."""
        result = parse_comma_separated_list("name,age,email")

        assert result == ["name", "age", "email"]

    def test_list_with_spaces(self) -> None:
        """Should trim spaces from items."""
        result = parse_comma_separated_list("name, age, email")

        assert result == ["name", "age", "email"]

    def test_list_with_extra_spaces(self) -> None:
        """Should handle extra spaces around items."""
        result = parse_comma_separated_list("  name  ,  age  ,  email  ")

        assert result == ["name", "age", "email"]

    def test_single_item(self) -> None:
        """Should handle single item without comma."""
        result = parse_comma_separated_list("name")

        assert result == ["name"]

    def test_single_item_with_spaces(self) -> None:
        """Should trim spaces from single item."""
        result = parse_comma_separated_list("  name  ")

        assert result == ["name"]

    def test_empty_string(self) -> None:
        """Should return list with empty string for empty input."""
        result = parse_comma_separated_list("")

        assert result == [""]

    def test_two_items(self) -> None:
        """Should handle two items."""
        result = parse_comma_separated_list("first, second")

        assert result == ["first", "second"]

    def test_class_names_with_underscores(self) -> None:
        """Should handle names with underscores."""
        result = parse_comma_separated_list("My_Class, Your_Class, Their_Class")

        assert result == ["My_Class", "Your_Class", "Their_Class"]

    def test_mixed_spacing(self) -> None:
        """Should handle inconsistent spacing."""
        result = parse_comma_separated_list("first,second, third,  fourth")

        assert result == ["first", "second", "third", "fourth"]
