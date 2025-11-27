"""Example code for inline-method with multiple call sites."""


class Person:
    def __init__(self, late_deliveries):
        self.late_deliveries = late_deliveries

    def get_rating(self):
        return 2 if self.late_deliveries > 5 else 1

    def is_problematic(self):
        return self.late_deliveries > 5

    def needs_review(self):
        if self.late_deliveries > 5:
            return "Needs immediate review"
        return "OK"
