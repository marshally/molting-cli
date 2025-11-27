"""Example code for separate query from modifier with name conflict."""


class Security:
    def __init__(self):
        self.intruders = []

    def get_and_remove_intruder(self):
        if len(self.intruders) > 0:
            intruder = self.intruders[0]
            self.intruders.pop(0)
            return intruder
        return None

    def get_intruder(self):
        """This method already exists - should conflict."""
        return "existing method"
