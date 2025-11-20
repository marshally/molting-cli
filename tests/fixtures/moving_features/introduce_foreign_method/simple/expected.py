from datetime import date, timedelta


class Report:
    def generate(self):
        previous_end = date(2023, 5, 31)
        new_start = self.next_day(previous_end)

    def next_day(self, arg):
        # Foreign method for date
        return arg + timedelta(days=1)
