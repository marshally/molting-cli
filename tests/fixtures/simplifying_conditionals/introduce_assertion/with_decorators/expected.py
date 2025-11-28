"""Example code for introduce assertion with decorators."""


class ExpenseManager:
    def __init__(self, project):
        self.project = project

    @property
    def expense_limit(self):
        assert (
            self.project.expense_limit is not None
            or self.project.primary_project is not None
        ), "Project must have expense limit or primary project"
        return (
            self.project.expense_limit
            if self.project.expense_limit
            else self.project.primary_project.member_expense_limit
        )
