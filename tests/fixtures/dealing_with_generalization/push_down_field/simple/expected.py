class Employee:
    pass


class Engineer(Employee):
    pass


class Salesman(Employee):
    def __init__(self):
        super().__init__()
        self.quota = 0
