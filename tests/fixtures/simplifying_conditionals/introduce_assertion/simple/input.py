def get_expense_limit(project):
    # Should have either expense limit or primary project
    return project.expense_limit if project.expense_limit else project.primary_project.member_expense_limit
