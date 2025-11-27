"""Example code for pull-up-constructor-body with name conflict."""


class Employee:
    def __init__(self, employee_id):
        # Constructor already exists with different signature
        self.employee_id = employee_id


class Manager(Employee):
    def __init__(self, name, id, grade):
        super().__init__(id)
        self.name = name
        self.id = id
        self.grade = grade


class Engineer(Employee):
    def __init__(self, name, id):
        super().__init__(id)
        self.name = name
        self.id = id
