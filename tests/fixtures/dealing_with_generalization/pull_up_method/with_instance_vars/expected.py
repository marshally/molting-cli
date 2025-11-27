class Employee:
    def __init__(self, name, base_salary):
        self.name = name
        self.base_salary = base_salary
        self.years_of_service = 0

    def get_employee_info(self):
        info = f"Name: {self.name}, Salary: {self.base_salary}"
        info += f", Years: {self.years_of_service}"
        return info


class Salesman(Employee):
    def __init__(self, name, base_salary, commission_rate):
        super().__init__(name, base_salary)
        self.commission_rate = commission_rate
        self.total_sales = 0


class Engineer(Employee):
    def __init__(self, name, base_salary, skill_level):
        super().__init__(name, base_salary)
        self.skill_level = skill_level
        self.projects_completed = 0
