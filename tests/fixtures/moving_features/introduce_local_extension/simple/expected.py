from datetime import date, timedelta


class MfDate(date):
    def next_day(self):
        return self + timedelta(days=1)

    def days_after(self, days):
        return self + timedelta(days=days)


# Client code
# new_start = previous_end.next_day()
