"""Example code for remove-middle-man with multiple call sites."""


class Person:
    def __init__(self, name, department):
        self.name = name
        self._department = department

    def get_manager(self):
        return self._department.manager

    def get_department_name(self):
        return self._department.name

    def get_budget(self):
        return self._department.budget


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
            managers.append(emp.get_manager())
        return managers

    def find_manager_for(self, person):
        return person.get_manager()

    def get_department_budget(self, employee):
        return employee.get_budget()


class Report:
    def generate_org_chart(self, people):
        chart = []
        for person in people:
            manager = person.get_manager()
            dept = person.get_department_name()
            chart.append(f"{person.name} ({dept}) reports to {manager}")
        return chart

    def total_budget(self, people):
        total = 0
        for person in people:
            total += person.get_budget()
        return total
