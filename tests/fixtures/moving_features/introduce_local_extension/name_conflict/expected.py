"""Example code for introduce-local-extension with name conflict."""

from datetime import date


class MfDate:
    """This class already exists - will conflict with local extension."""

    def existing_method(self):
        return "existing"


# Client code needs date calculations
# new_start = date(previous_end.year, previous_end.month, previous_end.day + 1)
