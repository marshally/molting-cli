"""Expected output after pull-up-field with multiple call sites."""


class Employee:
    def __init__(self, name):
        self.name = name


class Salesman(Employee):
    def __init__(self, name):
        super().__init__(name)
        self.sales_count = 0

    def record_sale(self):
        print(f"{self.name} made a sale")
        self.sales_count += 1

    def get_greeting(self):
        return f"Hello, I'm {self.name}, a salesman"

    def send_report(self):
        return f"Report from {self.name}: {self.sales_count} sales"


class Engineer(Employee):
    def __init__(self, name):
        super().__init__(name)
        self.projects_count = 0

    def start_project(self):
        print(f"{self.name} started a project")
        self.projects_count += 1

    def get_greeting(self):
        return f"Hello, I'm {self.name}, an engineer"

    def send_status(self):
        return f"Status from {self.name}: {self.projects_count} projects"


class Manager(Employee):
    def __init__(self, name):
        super().__init__(name)
        self.team_size = 0

    def add_team_member(self):
        print(f"{self.name} added a team member")
        self.team_size += 1

    def get_greeting(self):
        return f"Hello, I'm {self.name}, a manager"

    def team_report(self):
        return f"Team report from {self.name}: {self.team_size} members"
