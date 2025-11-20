from datetime import date


class Report:
    def generate(self):
        previous_end = date(2023, 5, 31)
        new_start = date(previous_end.year, previous_end.month, previous_end.day + 1)
