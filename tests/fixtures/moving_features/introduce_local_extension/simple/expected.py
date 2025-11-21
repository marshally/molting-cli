from datetime import date, timedelta


class MfDate(date):
    def next_day(self):
        return self + timedelta(days=1)

    def days_after(self, days):
        return self + timedelta(days=days)


# Client code using methods
previous_end = MfDate(2024, 1, 1)
new_start = previous_end.next_day()
result = previous_end.days_after(5)
