"""Example code for inline-method with multiple call sites."""


class Person:
    def __init__(self, late_deliveries):
        self.late_deliveries = late_deliveries

    def get_rating(self):
        return 2 if self.more_than_five_late_deliveries() else 1

    def is_problematic(self):
        return self.more_than_five_late_deliveries()

    def needs_review(self):
        if self.more_than_five_late_deliveries():
            return "Needs immediate review"
        return "OK"

    def more_than_five_late_deliveries(self):
        return self.late_deliveries > 5
