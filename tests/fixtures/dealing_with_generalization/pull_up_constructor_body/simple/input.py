class Employee:
    pass


class Manager(Employee):
    def __init__(self, name, id, grade):
        self.name = name
        self.id = id
        self.grade = grade


class Engineer(Employee):
    def __init__(self, name, id):
        self.name = name
        self.id = id
