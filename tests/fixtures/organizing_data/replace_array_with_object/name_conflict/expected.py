"""Example code for replace-array-with-object with name conflict."""


class Performance:
    """Existing class with the name we want to use."""

    def __init__(self):
        self.data = []


def analyze_performance(row):
    name = row[0]
    wins = row[1]
    losses = row[2]
    return f"{name}: {wins}W-{losses}L"
