"""Expected output after pull up constructor body with local variables."""


class Employee:
    def __init__(self, name, id):
        # Local variable used for validation
        normalized_name = name.strip().upper()
        self.name = normalized_name
        self.id = id


class Manager(Employee):
    def __init__(self, name, id, grade):
        super().__init__(name, id)
        self.grade = grade


class Engineer(Employee):
    def __init__(self, name, id):
        super().__init__(name, id)
