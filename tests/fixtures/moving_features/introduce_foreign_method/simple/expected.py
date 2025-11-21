from datetime import date


class Report:
    def generate(self):
        previous_end = date(2023, 5, 31)
        new_start = self.next_day(previous_end)

    def next_day(self, arg):
        return date(arg.year, arg.month, arg.day + 1)
