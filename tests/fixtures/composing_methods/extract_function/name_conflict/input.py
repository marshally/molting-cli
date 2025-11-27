"""Example code for extract function with name conflict."""


def normalize_string(s):
    """This function already exists - should cause conflict."""
    return s.upper()


class DataProcessor:
    def process(self, data):
        # format the data
        formatted = data.strip().lower().replace(" ", "_")
        return formatted
