"""Example code for remove-middle-man with multiple call sites."""


class Person:
    def __init__(self, name, department):
        self.name = name
        self.department = department


class Department:
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.budget = 100000


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

    def get_department_budget(self, employee):
        return employee.department.budget


class Report:
    def generate_org_chart(self, people):
        chart = []
        for person in people:
            manager = person.department.manager
            dept = person.department.name
            chart.append(f"{person.name} ({dept}) reports to {manager}")
        return chart

    def total_budget(self, people):
        total = 0
        for person in people:
            total += person.department.budget
        return total
