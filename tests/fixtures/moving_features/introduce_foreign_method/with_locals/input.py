"""Example code for introduce foreign method with local variables."""

from datetime import date


class Report:
    def generate(self):
        start_date = date(2023, 5, 31)
        days_to_add = 7
        offset = 3
        total_days = days_to_add + offset
        end_date = date(
            start_date.year, start_date.month, start_date.day + total_days
        )
