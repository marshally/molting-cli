"""Tests for CallSiteUpdater utility.

This module tests the CallSiteUpdater class which finds and updates all call sites
to use new method/function names or patterns when transformers modify API signatures.
"""

import libcst as cst

from molting.core.call_site_updater import AttributeCallReplacer, CallSiteUpdater


class TestAttributeCallReplacer:
    """Tests for AttributeCallReplacer visitor."""

    def test_replace_single_attribute_call(self) -> None:
        """Test replacing a single attribute call like obj.method() -> obj.new_method()."""
        code = """
result = person.get_department()
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer("person", "get_department", "get_manager")
        modified = module.visit(replacer)

        expected = """
result = person.get_manager()
"""
        assert modified.code == expected.strip()

    def test_replace_nested_attribute_call(self) -> None:
        """Test replacing nested attribute calls like obj.delegate.method() -> obj.method()."""
        code = """
manager = person.department.manager
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer(
            object_name="person",
            old_attr="department",
            new_method="get_manager",
            nested_attr="manager",
        )
        modified = module.visit(replacer)

        expected = """
manager = person.get_manager()
"""
        assert modified.code == expected.strip()

    def test_replace_multiple_occurrences(self) -> None:
        """Test replacing multiple occurrences in same code."""
        code = """
m1 = person.department.manager
m2 = person.department.manager
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer(
            object_name="person",
            old_attr="department",
            new_method="get_manager",
            nested_attr="manager",
        )
        modified = module.visit(replacer)

        expected = """
m1 = person.get_manager()
m2 = person.get_manager()
"""
        assert modified.code == expected.strip()

    def test_preserve_different_calls(self) -> None:
        """Test that different object/attribute calls are not modified."""
        code = """
manager = person.department.manager
other = employee.department.manager
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer(
            object_name="person",
            old_attr="department",
            new_method="get_manager",
            nested_attr="manager",
        )
        modified = module.visit(replacer)

        # Only person.department.manager should be replaced
        expected = """
manager = person.get_manager()
other = employee.department.manager
"""
        assert modified.code == expected.strip()

    def test_replace_direct_constructor_calls(self) -> None:
        """Test replacing direct constructor calls with factory function."""
        code = """
emp = Employee(Employee.ENGINEER)
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer(class_name="Employee", factory_name="create_employee")
        modified = module.visit(replacer)

        expected = """
emp = create_employee(Employee.ENGINEER)
"""
        assert modified.code == expected.strip()

    def test_replace_multiple_constructor_calls(self) -> None:
        """Test replacing multiple constructor calls."""
        code = """
e1 = Employee(Employee.ENGINEER)
e2 = Employee(Employee.MANAGER)
e3 = Employee(role_type)
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer(class_name="Employee", factory_name="create_employee")
        modified = module.visit(replacer)

        expected = """
e1 = create_employee(Employee.ENGINEER)
e2 = create_employee(Employee.MANAGER)
e3 = create_employee(role_type)
"""
        assert modified.code == expected.strip()

    def test_preserve_other_class_constructors(self) -> None:
        """Test that other constructors are not modified."""
        code = """
emp = Employee(Employee.ENGINEER)
dept = Department()
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer(class_name="Employee", factory_name="create_employee")
        modified = module.visit(replacer)

        expected = """
emp = create_employee(Employee.ENGINEER)
dept = Department()
"""
        assert modified.code == expected.strip()

    def test_handle_method_call_with_nested_attribute(self) -> None:
        """Test replacing method call with nested attribute access."""
        code = """
managers = []
for emp in self.employees:
    managers.append(emp.department.manager)
"""
        module = cst.parse_module(code.strip())
        replacer = AttributeCallReplacer(
            object_name="emp",
            old_attr="department",
            new_method="get_manager",
            nested_attr="manager",
        )
        modified = module.visit(replacer)

        expected = """
managers = []
for emp in self.employees:
    managers.append(emp.get_manager())
"""
        assert modified.code == expected.strip()


class TestCallSiteUpdater:
    """Tests for CallSiteUpdater main class."""

    def test_find_and_update_hide_delegate_calls(self) -> None:
        """Test finding and updating call sites for hide_delegate pattern."""
        code = """
class Company:
    def find_manager_for(self, person):
        return person.department.manager

def get_reporting_line(person):
    return f"{person.name} -> {person.department.manager}"
"""
        module = cst.parse_module(code.strip())
        updater = CallSiteUpdater(
            object_name="person",
            old_attr="department",
            new_method="get_manager",
            nested_attr="manager",
        )
        modified = module.visit(updater)

        expected = """
class Company:
    def find_manager_for(self, person):
        return person.get_manager()

def get_reporting_line(person):
    return f"{person.name} -> {person.get_manager()}"
"""
        assert modified.code == expected.strip()

    def test_find_and_update_hide_delegate_any_object(self) -> None:
        """Test finding and updating call sites when no object_name restriction."""
        code = """
class Company:
    def get_all_managers(self):
        managers = []
        for emp in self.employees:
            managers.append(emp.department.manager)
        return managers

    def find_manager_for(self, person):
        return person.department.manager

def get_reporting_line(person):
    return f"{person.name} -> {person.department.manager}"
"""
        module = cst.parse_module(code.strip())
        # When object_name is None, replace ALL occurrences of the pattern
        updater = CallSiteUpdater(
            old_attr="department",
            new_method="get_manager",
            nested_attr="manager",
        )
        modified = module.visit(updater)

        expected = """
class Company:
    def get_all_managers(self):
        managers = []
        for emp in self.employees:
            managers.append(emp.get_manager())
        return managers

    def find_manager_for(self, person):
        return person.get_manager()

def get_reporting_line(person):
    return f"{person.name} -> {person.get_manager()}"
"""
        assert modified.code == expected.strip()

    def test_find_and_update_factory_calls(self) -> None:
        """Test finding and updating constructor call sites for factory pattern."""
        code = """
class Department:
    def hire_engineer(self):
        emp = Employee(Employee.ENGINEER)
        self.employees.append(emp)
        return emp

def create_sales_team(size):
    team = []
    for i in range(size):
        team.append(Employee(Employee.SALESMAN))
    return team

def onboard_employee(role_type):
    employee = Employee(role_type)
    print(f"Onboarding employee of type {role_type}")
    return employee
"""
        module = cst.parse_module(code.strip())
        updater = CallSiteUpdater(class_name="Employee", factory_name="create_employee")
        modified = module.visit(updater)

        expected = """
class Department:
    def hire_engineer(self):
        emp = create_employee(Employee.ENGINEER)
        self.employees.append(emp)
        return emp

def create_sales_team(size):
    team = []
    for i in range(size):
        team.append(create_employee(Employee.SALESMAN))
    return team

def onboard_employee(role_type):
    employee = create_employee(role_type)
    print(f"Onboarding employee of type {role_type}")
    return employee
"""
        assert modified.code == expected.strip()

    def test_no_changes_when_no_matches(self) -> None:
        """Test that code is unchanged when no matching calls found."""
        code = """
def some_function():
    x = 42
    return x
"""
        module = cst.parse_module(code.strip())
        updater = CallSiteUpdater(
            object_name="person",
            old_attr="department",
            new_method="get_manager",
            nested_attr="manager",
        )
        modified = module.visit(updater)

        assert modified.code == code.strip()

    def test_exclude_factory_function_from_replacement(self) -> None:
        """Test that constructor calls inside the factory function are not replaced."""
        code = """
def create_employee(employee_type):
    return Employee(employee_type)

emp = Employee(Employee.ENGINEER)
"""
        module = cst.parse_module(code.strip())
        updater = CallSiteUpdater(class_name="Employee", factory_name="create_employee")
        modified = module.visit(updater)

        # The Employee() call inside the factory should stay, but the one outside should change
        expected = """
def create_employee(employee_type):
    return Employee(employee_type)

emp = create_employee(Employee.ENGINEER)
"""
        assert modified.code == expected.strip()
