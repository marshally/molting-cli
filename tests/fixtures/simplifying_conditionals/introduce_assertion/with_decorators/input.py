"""Example code for introduce assertion with decorators."""


class ExpenseManager:
    def __init__(self, project):
        self.project = project

    @property
    def expense_limit(self):
        # Should have either expense limit or primary project
        return (
            self.project.expense_limit
            if self.project.expense_limit
            else self.project.primary_project.member_expense_limit
        )
