"""Expected output after introduce-assertion with instance variables."""


class ExpenseManager:
    def __init__(self, default_limit=1000):
        self.default_limit = default_limit
        self.override_limit = None

    def get_expense_limit(self, project):
        assert (
            project.expense_limit is not None or project.primary_project is not None
        ), "Project must have expense limit or primary project"
        # Should have either expense limit or primary project
        if self.override_limit is not None:
            return self.override_limit
        return (
            project.expense_limit
            if project.expense_limit
            else project.primary_project.member_expense_limit
        )
