"""Example code for introduce foreign method with local variables."""

from datetime import date, timedelta


class Report:
    def generate(self):
        start_date = date(2023, 5, 31)
        days_to_add = 7
        offset = 3
        total_days = days_to_add + offset
        end_date = self.add_days(start_date, total_days)

    def add_days(self, arg, total_days):
        # Foreign method for date
        return arg + timedelta(days=total_days)
