from datetime import date, timedelta


def next_day(a_date):
    return a_date + timedelta(days=1)


def days_after(a_date, days):
    return a_date + timedelta(days=days)


# Client code using helper functions
previous_end = date(2024, 1, 1)
new_start = next_day(previous_end)
result = days_after(previous_end, 5)
