def get_expense_limit(project):
    assert (
        project.expense_limit is not None or project.primary_project is not None
    ), "Project must have expense limit or primary project"
    return (
        project.expense_limit
        if project.expense_limit
        else project.primary_project.member_expense_limit
    )
