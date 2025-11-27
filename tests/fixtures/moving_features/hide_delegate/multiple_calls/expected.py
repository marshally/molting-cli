"""Expected output after hide-delegate with multiple call sites."""


class Person:
    def __init__(self, name, department):
        self.name = name
        self._department = department

    def get_manager(self):
        return self._department.manager


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
            managers.append(emp.get_manager())
        return managers

    def find_manager_for(self, person):
        return person.get_manager()

    def department_head(self, employee):
        return employee.get_manager()


class Report:
    def generate_org_chart(self, people):
        chart = []
        for person in people:
            manager = person.get_manager()
            chart.append(f"{person.name} reports to {manager}")
        return chart

    def get_reporting_line(self, person):
        return f"{person.name} -> {person.get_manager()}"
