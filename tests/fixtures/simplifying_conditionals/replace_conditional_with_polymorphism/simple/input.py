class Employee:
    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.base_salary = 1000
        self.bonus = 500

    def pay_amount(self):
        if self.type == "engineer":
            return self.base_salary
        elif self.type == "manager":
            return self.base_salary + self.bonus
        elif self.type == "intern":
            return self.base_salary * 0.5
        else:
            raise ValueError(f"Unknown employee type: {self.type}")
