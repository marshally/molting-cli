"""Example code for pull up constructor body with local variables."""


class Employee:
    pass


class Manager(Employee):
    def __init__(self, name, id, grade):
        # Local variable used for validation
        normalized_name = name.strip().upper()
        self.name = normalized_name
        self.id = id
        self.grade = grade


class Engineer(Employee):
    def __init__(self, name, id):
        # Same local variable pattern
        normalized_name = name.strip().upper()
        self.name = normalized_name
        self.id = id
