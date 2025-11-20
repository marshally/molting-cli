class Performance:
    def __init__(self, name, wins, losses):
        self.name = name
        self.wins = wins
        self.losses = losses


def analyze_performance(performance):
    name = performance.name
    wins = performance.wins
    losses = performance.losses
    return f"{name}: {wins}W-{losses}L"
