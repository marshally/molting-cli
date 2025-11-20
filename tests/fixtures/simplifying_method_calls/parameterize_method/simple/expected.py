class Employee:
    def __init__(self, salary):
        self.salary = salary

    def raise_salary(self, percentage):
        self.salary *= (1 + percentage / 100)

    def five_percent_raise(self):
        self.raise_salary(5)

    def ten_percent_raise(self):
        self.raise_salary(10)
