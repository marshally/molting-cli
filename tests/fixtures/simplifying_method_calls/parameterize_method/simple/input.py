class Employee:
    def __init__(self, salary):
        self.salary = salary

    def five_percent_raise(self):
        self.salary *= 1.05

    def ten_percent_raise(self):
        self.salary *= 1.10
