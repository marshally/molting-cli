"""
Tests for CST visitor classes.

This module tests the reusable visitor classes used across refactorings,
including the SelfFieldCollector for finding self.field references.
"""

import libcst as cst

from molting.core.visitors import SelfFieldCollector


class TestSelfFieldCollector:
    """Tests for SelfFieldCollector visitor."""

    def test_collects_single_self_field(self) -> None:
        """Should collect a single self.field reference."""
        code = """
def method(self):
    return self.name
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = SelfFieldCollector()
        method.visit(collector)

        assert collector.collected_fields == ["name"]

    def test_collects_multiple_self_fields(self) -> None:
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

        collector = SelfFieldCollector()
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

        collector = SelfFieldCollector(exclude_fields={"age"})
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

        collector = SelfFieldCollector()
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

        collector = SelfFieldCollector()
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

        collector = SelfFieldCollector()
        method.visit(collector)

        assert len(collector.collected_fields) == 4
        assert "name" in collector.collected_fields
        assert "age" in collector.collected_fields
        assert "active" in collector.collected_fields
        assert "default" in collector.collected_fields

    def test_collects_from_assignments(self) -> None:
        """Should collect self.field from assignment targets."""
        code = """
def method(self):
    self.name = "test"
    self.age = 30
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = SelfFieldCollector()
        method.visit(collector)

        assert len(collector.collected_fields) == 2
        assert "name" in collector.collected_fields
        assert "age" in collector.collected_fields

    def test_empty_method(self) -> None:
        """Should return empty list for method with no self references."""
        code = """
def method(self):
    x = 5
    return x
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = SelfFieldCollector()
        method.visit(collector)

        assert collector.collected_fields == []

    def test_collects_from_method_calls(self) -> None:
        """Should collect self.field from method calls."""
        code = """
def method(self):
    self.calculate()
    return self.process(self.data)
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = SelfFieldCollector()
        method.visit(collector)

        assert len(collector.collected_fields) == 3
        assert "calculate" in collector.collected_fields
        assert "process" in collector.collected_fields
        assert "data" in collector.collected_fields

    def test_exclude_fields_with_none(self) -> None:
        """Should handle None exclude_fields parameter."""
        code = """
def method(self):
    return self.name
"""
        module = cst.parse_module(code)
        method = module.body[0]
        assert isinstance(method, cst.FunctionDef)

        collector = SelfFieldCollector(exclude_fields=None)
        method.visit(collector)

        assert collector.collected_fields == ["name"]
