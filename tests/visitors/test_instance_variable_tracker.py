"""Tests for InstanceVariableTracker utility.

Tests for the InstanceVariableTracker helper that detects class method context,
tracks self.attribute references, and determines if extracted code needs self.
"""

import libcst as cst

from molting.core.instance_variable_tracker import InstanceVariableTracker


class TestInstanceVariableTrackerIsMethod:
    """Tests for detecting if code is inside a class method."""

    def test_detects_code_inside_class_method(self) -> None:
        """Should detect that code is inside a class method."""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Calculator", "add")
        assert tracker.is_method() is True

    def test_detects_standalone_function(self) -> None:
        """Should detect that code is NOT inside a class method."""
        code = """
def add(a, b):
    return a + b
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "", "add")
        assert tracker.is_method() is False

    def test_detects_static_method(self) -> None:
        """Should detect static methods as not requiring self."""
        code = """
class Calculator:
    @staticmethod
    def add(a, b):
        return a + b
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Calculator", "add")
        # Static methods don't have self, so is_method should be False
        assert tracker.is_method() is False

    def test_detects_class_method(self) -> None:
        """Should detect class methods (decorated with @classmethod)."""
        code = """
class Calculator:
    @classmethod
    def create(cls):
        return cls()
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Calculator", "create")
        # Class methods have cls, not self, so is_method should be False
        assert tracker.is_method() is False


class TestInstanceVariableTrackerSelfReferences:
    """Tests for collecting self.attribute references."""

    def test_collects_simple_self_references(self) -> None:
        """Should collect simple self.attribute references."""
        code = """
class PricingCalculator:
    def __init__(self):
        self.winter_rate = 5
        self.summer_rate = 10

    def calculate_charge(self, quantity):
        charge = quantity * self.winter_rate
        return charge
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "PricingCalculator", "calculate_charge")
        self_refs = tracker.collect_self_references()
        assert "winter_rate" in self_refs

    def test_collects_multiple_self_references(self) -> None:
        """Should collect all unique self.attribute references."""
        code = """
class PricingCalculator:
    def calculate_charge(self, quantity):
        if self.is_winter:
            charge = quantity * self.winter_rate
        else:
            charge = quantity * self.summer_rate + self.service_charge
        return charge
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "PricingCalculator", "calculate_charge")
        self_refs = tracker.collect_self_references()
        assert "is_winter" in self_refs
        assert "winter_rate" in self_refs
        assert "summer_rate" in self_refs
        assert "service_charge" in self_refs

    def test_deduplicates_self_references(self) -> None:
        """Should return unique self references only once."""
        code = """
class Calculator:
    def process(self):
        x = self.value
        y = self.value
        z = self.value
        return x + y + z
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Calculator", "process")
        self_refs = tracker.collect_self_references()
        assert self_refs.count("value") == 1

    def test_ignores_non_self_references(self) -> None:
        """Should ignore attribute accesses on other objects."""
        code = """
class Processor:
    def process(self):
        external_obj = SomeClass()
        x = external_obj.value
        y = self.my_value
        return x + y
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Processor", "process")
        self_refs = tracker.collect_self_references()
        assert "value" not in self_refs  # This is on external_obj, not self
        assert "my_value" in self_refs


class TestInstanceVariableTrackerNeedsself:
    """Tests for determining if extracted code needs self parameter."""

    def test_code_with_self_references_needs_self(self) -> None:
        """Should return True when code uses self.attribute."""
        code = """
class PricingCalculator:
    def calculate_charge(self, quantity):
        charge = quantity * self.winter_rate + self.service_charge
        return charge
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "PricingCalculator", "calculate_charge")
        assert tracker.needs_self_parameter() is True

    def test_code_without_self_references_no_self(self) -> None:
        """Should return False when code doesn't use self.attribute."""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Calculator", "add")
        assert tracker.needs_self_parameter() is False

    def test_standalone_function_no_self(self) -> None:
        """Should return False for standalone functions."""
        code = """
def add(a, b):
    return a + b
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "", "add")
        assert tracker.needs_self_parameter() is False

    def test_method_referencing_self_methods_needs_self(self) -> None:
        """Should return True when code calls self.method()."""
        code = """
class Validator:
    def is_valid(self):
        return True

    def validate(self):
        return self.is_valid()
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Validator", "validate")
        assert tracker.needs_self_parameter() is True


class TestInstanceVariableTrackerForCodeBlock:
    """Tests for analyzing extracted code blocks specifically."""

    def test_extracted_block_with_self_references(self) -> None:
        """Should identify self references in a specific code block."""
        code = """
class PricingCalculator:
    def calculate_charge(self, quantity, date):
        if date.month < 6 or date.month > 8:
            charge = quantity * self.winter_rate + self.winter_service_charge
        else:
            charge = quantity * self.summer_rate
        return charge
"""
        module = cst.parse_module(code)
        # Extract the if statement's body
        tracker = InstanceVariableTracker(module, "PricingCalculator", "calculate_charge")

        # The extracted block uses self.winter_rate, self.winter_service_charge
        self_refs = tracker.collect_self_references()
        assert "winter_rate" in self_refs
        assert "winter_service_charge" in self_refs
        assert "summer_rate" in self_refs

    def test_extracted_condition_with_self_references(self) -> None:
        """Should identify self references in extracted conditions."""
        code = """
class DuplicateRemover:
    def remove_duplicate_lines(self):
        lines = []
        for line in self.input_lines:
            if self.is_duplicate(line):
                continue
            lines.append(line)
        return lines
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "DuplicateRemover", "remove_duplicate_lines")
        self_refs = tracker.collect_self_references()
        assert "input_lines" in self_refs
        assert "is_duplicate" in self_refs


class TestInstanceVariableTrackerWithNestedClasses:
    """Tests for handling nested class scenarios."""

    def test_finds_method_in_correct_class(self) -> None:
        """Should find method in the correct class when there are nested classes."""
        code = """
class Outer:
    def outer_method(self):
        return self.outer_value

    class Inner:
        def inner_method(self):
            return self.inner_value
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Outer", "outer_method")
        self_refs = tracker.collect_self_references()
        assert "outer_value" in self_refs
        assert "inner_value" not in self_refs


class TestInstanceVariableTrackerCollectInitVars:
    """Tests for collecting instance variables defined in __init__."""

    def test_collects_instance_variables_from_init(self) -> None:
        """Should collect all instance variables defined in __init__."""
        code = """
class PricingCalculator:
    def __init__(self, winter_rate, summer_rate, winter_service_charge):
        self.winter_rate = winter_rate
        self.summer_rate = summer_rate
        self.winter_service_charge = winter_service_charge

    def calculate_charge(self, quantity):
        return quantity * self.winter_rate
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "PricingCalculator", "__init__")
        init_vars = tracker.collect_init_instance_variables()
        assert "winter_rate" in init_vars
        assert "summer_rate" in init_vars
        assert "winter_service_charge" in init_vars

    def test_collects_no_init_vars_if_no_init(self) -> None:
        """Should return empty list if __init__ doesn't exist."""
        code = """
class Simple:
    def method(self):
        self.value = 10
        return self.value
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Simple", "method")
        init_vars = tracker.collect_init_instance_variables()
        assert len(init_vars) == 0

    def test_collects_annotated_instance_variables(self) -> None:
        """Should collect annotated instance variables from __init__."""
        code = """
class Example:
    def __init__(self):
        self.count: int = 0
        self.name: str = "test"
"""
        module = cst.parse_module(code)
        tracker = InstanceVariableTracker(module, "Example", "__init__")
        init_vars = tracker.collect_init_instance_variables()
        assert "count" in init_vars
        assert "name" in init_vars
