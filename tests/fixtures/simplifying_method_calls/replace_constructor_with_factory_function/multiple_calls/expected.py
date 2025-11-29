class Employee:
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary


def create_employee(name, salary):
    return Employee(name, salary)


class Department:
    def __init__(self):
        self.employees = []

    def hire(self, name, salary):
        emp = create_employee(name, salary)
        self.employees.append(emp)
        return emp


def create_team(members):
    team = []
    for name, salary in members:
        team.append(create_employee(name, salary))
    return team
