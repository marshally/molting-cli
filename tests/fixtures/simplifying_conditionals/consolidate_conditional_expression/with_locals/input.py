"""Expected output after consolidate conditional expression with local variables."""


def calculate_bonus(employee, performance_score):
    # Local variables used in conditional
    min_score = 75
    min_years = 2
    bonus_threshold = 1000

    if performance_score < min_score:
        return 0
    if employee.years_of_service < min_years:
        return 0
    if employee.total_sales < bonus_threshold:
        return 0

    # calculate bonus
    return employee.total_sales * 0.10
