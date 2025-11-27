"""Example code for separate query from modifier with name conflict."""


class Security:
    def __init__(self):
        self.intruders = []

    def get_intruder(self):
        if len(self.intruders) > 0:
            return self.intruders[0]
        return None

    def remove_intruder(self):
        if len(self.intruders) > 0:
            self.intruders.pop(0)

    def get_intruder(self):
        """This method already exists - should conflict."""
        return "existing method"
