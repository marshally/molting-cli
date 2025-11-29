class Employee:
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary


class Department:
    def __init__(self):
        self.employees = []

    def hire(self, name, salary):
        emp = Employee(name, salary)
        self.employees.append(emp)
        return emp


def create_team(members):
    team = []
    for name, salary in members:
        team.append(Employee(name, salary))
    return team
