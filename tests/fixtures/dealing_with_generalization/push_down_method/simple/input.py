class Employee:
    def __init__(self, name):
        self.name = name

    def get_quota(self):
        return 100


class Salesman(Employee):
    pass


class Engineer(Employee):
    pass
