"""Example code for hide-delegate with multiple call sites."""


class Person:
    def __init__(self, name, department):
        self.name = name
        self.department = department


class Department:
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager


class Company:
    def __init__(self):
        self.employees = []

    def get_all_managers(self):
        managers = []
        for emp in self.employees:
            managers.append(emp.department.manager)
        return managers

    def find_manager_for(self, person):
        return person.department.manager

    def department_head(self, employee):
        return employee.department.manager


class Report:
    def generate_org_chart(self, people):
        chart = []
        for person in people:
            manager = person.department.manager
            chart.append(f"{person.name} reports to {manager}")
        return chart

    def get_reporting_line(self, person):
        return f"{person.name} -> {person.department.manager}"
