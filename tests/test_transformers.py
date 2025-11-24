"""
Tests for CST transformer classes.

This module tests the reusable transformer classes used across refactorings,
including SelfFieldRenameTransformer for renaming self.field references
and FieldAccessCollector for collecting field accesses.
"""

import libcst as cst
import pytest

from molting.core.transformers import FieldAccessCollector, SelfFieldRenameTransformer


class TestSelfFieldRenameTransformer:
    """Tests for SelfFieldRenameTransformer."""

    def test_field_mapping_simple_rename(self) -> None:
        """Should rename fields using field_mapping."""
        code = """
def method(self):
    return self.old_name
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_mapping={"old_name": "new_name"})
        modified = module.visit(transformer)

        assert "self.new_name" in modified.code
        assert "self.old_name" not in modified.code

    def test_field_mapping_multiple_fields(self) -> None:
        """Should rename multiple fields using field_mapping."""
        code = """
def method(self):
    x = self.foo
    y = self.bar
    return self.baz
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(
            field_mapping={"foo": "alpha", "bar": "beta", "baz": "gamma"}
        )
        modified = module.visit(transformer)

        assert "self.alpha" in modified.code
        assert "self.beta" in modified.code
        assert "self.gamma" in modified.code
        assert "self.foo" not in modified.code
        assert "self.bar" not in modified.code
        assert "self.baz" not in modified.code

    def test_field_prefix_simple(self) -> None:
        """Should add prefix to specified fields."""
        code = """
def method(self):
    return self.name
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_prefix="_", field_names={"name"})
        modified = module.visit(transformer)

        assert "self._name" in modified.code
        assert "self.name" not in modified.code

    def test_field_prefix_multiple_fields(self) -> None:
        """Should add prefix to multiple specified fields."""
        code = """
def method(self):
    x = self.foo
    y = self.bar
    return self.baz
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(
            field_prefix="private_", field_names={"foo", "bar"}
        )
        modified = module.visit(transformer)

        assert "self.private_foo" in modified.code
        assert "self.private_bar" in modified.code
        assert "self.baz" in modified.code  # Not in field_names, so not changed

    def test_field_prefix_not_in_field_names(self) -> None:
        """Should only prefix fields that are in field_names."""
        code = """
def method(self):
    x = self.name
    y = self.age
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_prefix="_", field_names={"name"})
        modified = module.visit(transformer)

        assert "self._name" in modified.code
        assert "self.age" in modified.code  # Not prefixed

    def test_transform_fn_simple(self) -> None:
        """Should apply custom transform function."""
        code = """
def method(self):
    return self.name
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(
            field_names={"name"}, transform_fn=lambda n: f"_{n}_private"
        )
        modified = module.visit(transformer)

        assert "self._name_private" in modified.code
        assert "self.name" not in modified.code

    def test_transform_fn_multiple_fields(self) -> None:
        """Should apply custom transform to multiple fields."""
        code = """
def method(self):
    x = self.foo
    y = self.bar
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(
            field_names={"foo", "bar"}, transform_fn=lambda n: n.upper()
        )
        modified = module.visit(transformer)

        assert "self.FOO" in modified.code
        assert "self.BAR" in modified.code

    def test_ignores_non_self_attributes(self) -> None:
        """Should not transform attributes from other objects."""
        code = """
def method(self):
    obj = Object()
    return obj.name
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_mapping={"name": "new_name"})
        modified = module.visit(transformer)

        assert "obj.name" in modified.code  # Not changed
        assert "obj.new_name" not in modified.code

    def test_transforms_in_assignments(self) -> None:
        """Should transform self.field in assignment targets."""
        code = """
def method(self):
    self.name = "test"
    self.age = 30
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(
            field_mapping={"name": "full_name", "age": "years"}
        )
        modified = module.visit(transformer)

        assert "self.full_name" in modified.code
        assert "self.years" in modified.code
        assert "self.name" not in modified.code
        assert "self.age" not in modified.code

    def test_transforms_in_nested_expressions(self) -> None:
        """Should transform self.field in nested expressions."""
        code = """
def method(self):
    return self.name + self.age if self.active else self.default
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(
            field_mapping={"name": "full_name", "age": "years", "active": "is_active"}
        )
        modified = module.visit(transformer)

        assert "self.full_name" in modified.code
        assert "self.years" in modified.code
        assert "self.is_active" in modified.code
        assert "self.default" in modified.code  # Not in mapping

    def test_field_mapping_takes_priority(self) -> None:
        """field_mapping should be applied before prefix/transform_fn."""
        code = """
def method(self):
    x = self.foo
    y = self.bar
"""
        module = cst.parse_module(code)
        # foo is in field_mapping, bar uses prefix
        transformer = SelfFieldRenameTransformer(
            field_mapping={"foo": "renamed_foo"},
            field_prefix="_",
            field_names={"foo", "bar"},
        )
        modified = module.visit(transformer)

        assert "self.renamed_foo" in modified.code  # Used mapping
        assert "self._bar" in modified.code  # Used prefix
        assert "self._foo" not in modified.code  # Mapping took priority

    def test_requires_configuration(self) -> None:
        """Should raise error if no transformation mode is provided."""
        with pytest.raises(ValueError, match="Must provide at least one of"):
            SelfFieldRenameTransformer()

    def test_requires_field_names_with_prefix(self) -> None:
        """Should raise error if field_prefix is used without field_names."""
        with pytest.raises(ValueError, match="field_names must be provided"):
            SelfFieldRenameTransformer(field_prefix="_")

    def test_requires_field_names_with_transform_fn(self) -> None:
        """Should raise error if transform_fn is used without field_names."""
        with pytest.raises(ValueError, match="field_names must be provided"):
            SelfFieldRenameTransformer(transform_fn=lambda n: f"_{n}")

    def test_field_mapping_alone_is_valid(self) -> None:
        """Should allow field_mapping without field_names."""
        # Should not raise
        transformer = SelfFieldRenameTransformer(field_mapping={"foo": "bar"})
        assert transformer.field_mapping == {"foo": "bar"}

    def test_no_transformation_when_field_not_matched(self) -> None:
        """Should leave field unchanged if not in mapping or field_names."""
        code = """
def method(self):
    return self.untouched
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_mapping={"other": "renamed"})
        modified = module.visit(transformer)

        assert "self.untouched" in modified.code

    def test_complex_scenario_remove_prefix(self) -> None:
        """Should handle removing office_ prefix from fields."""
        code = """
def method(self):
    return self.office_number + self.office_area_code
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(
            field_mapping={"office_number": "number", "office_area_code": "area_code"}
        )
        modified = module.visit(transformer)

        assert "self.number" in modified.code
        assert "self.area_code" in modified.code
        assert "office_" not in modified.code

    def test_private_field_pattern(self) -> None:
        """Should handle converting public to private fields."""
        code = """
class Person:
    def __init__(self):
        self.name = "John"
        self.age = 30
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_prefix="_", field_names={"name", "age"})
        modified = module.visit(transformer)

        assert "self._name" in modified.code
        assert "self._age" in modified.code

    def test_method_call_on_self_field(self) -> None:
        """Should transform self.field when it's followed by method calls."""
        code = """
def method(self):
    return self.manager.get_name()
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_mapping={"manager": "_manager"})
        modified = module.visit(transformer)

        assert "self._manager.get_name()" in modified.code
        assert "self.manager" not in modified.code

    def test_chained_attributes_only_transforms_self(self) -> None:
        """Should only transform the self.field part of chained attributes."""
        code = """
def method(self):
    return self.person.manager.name
"""
        module = cst.parse_module(code)
        transformer = SelfFieldRenameTransformer(field_mapping={"person": "_person"})
        modified = module.visit(transformer)

        assert "self._person.manager.name" in modified.code


class TestFieldAccessCollector:
    """Tests for FieldAccessCollector visitor."""

    def test_collects_single_field(self) -> None:
        """Should collect a single self.field reference."""
        code = """
def method(self):
    return self.name
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector()
        method.visit(collector)

        assert collector.collected_fields == ["name"]

    def test_collects_multiple_fields(self) -> None:
        """Should collect all self.field references."""
        code = """
def method(self):
    x = self.name
    y = self.age
    return self.email
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector()
        method.visit(collector)

        assert len(collector.collected_fields) == 3
        assert "name" in collector.collected_fields
        assert "age" in collector.collected_fields
        assert "email" in collector.collected_fields

    def test_excludes_specified_fields(self) -> None:
        """Should not collect fields in exclude_fields set."""
        code = """
def method(self):
    x = self.name
    y = self.age
    return self.email
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector(exclude_fields={"age"})
        method.visit(collector)

        assert len(collector.collected_fields) == 2
        assert "name" in collector.collected_fields
        assert "email" in collector.collected_fields
        assert "age" not in collector.collected_fields

    def test_no_duplicate_fields(self) -> None:
        """Should not include duplicate fields."""
        code = """
def method(self):
    x = self.name
    y = self.name
    return self.name
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector()
        method.visit(collector)

        assert collector.collected_fields == ["name"]

    def test_ignores_non_self_attributes(self) -> None:
        """Should not collect attributes from other objects."""
        code = """
def method(self):
    obj = Object()
    return obj.name
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector()
        method.visit(collector)

        assert collector.collected_fields == []

    def test_collects_from_nested_expressions(self) -> None:
        """Should collect self.field from nested expressions."""
        code = """
def method(self):
    return self.name + self.age if self.active else self.default
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector()
        method.visit(collector)

        assert len(collector.collected_fields) == 4
        assert "name" in collector.collected_fields
        assert "age" in collector.collected_fields
        assert "active" in collector.collected_fields
        assert "default" in collector.collected_fields

    def test_empty_when_no_self_references(self) -> None:
        """Should return empty list for code with no self references."""
        code = """
def method(self):
    x = 5
    return x
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector()
        method.visit(collector)

        assert collector.collected_fields == []

    def test_exclude_fields_none(self) -> None:
        """Should handle None exclude_fields parameter."""
        code = """
def method(self):
    return self.name
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = FieldAccessCollector(exclude_fields=None)
        method.visit(collector)

        assert collector.collected_fields == ["name"]
