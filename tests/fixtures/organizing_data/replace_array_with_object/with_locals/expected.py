"""Expected output after replace array with object with local variables."""


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


def calculate_win_rate(performance):
    # Using array elements in local variable computations
    total_games = performance.wins + performance.losses
    wins = performance.wins

    if total_games == 0:
        return 0.0

    win_rate = wins / total_games
    percentage = win_rate * 100
    return round(percentage, 2)


def format_record(performance):
    # Multiple local variables processing array elements
    player_name = performance.name.upper()
    win_count = performance.wins
    loss_count = performance.losses

    total = win_count + loss_count
    ratio = f"{win_count}/{total}" if total > 0 else "N/A"

    return f"{player_name}: {ratio}"
