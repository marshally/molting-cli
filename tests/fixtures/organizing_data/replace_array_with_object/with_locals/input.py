"""Example code for replace array with object with local variables."""


def analyze_performance(row):
    name = row[0]
    wins = row[1]
    losses = row[2]
    return f"{name}: {wins}W-{losses}L"


def calculate_win_rate(row):
    # Using array elements in local variable computations
    total_games = row[1] + row[2]
    wins = row[1]

    if total_games == 0:
        return 0.0

    win_rate = wins / total_games
    percentage = win_rate * 100
    return round(percentage, 2)


def format_record(row):
    # Multiple local variables processing array elements
    player_name = row[0].upper()
    win_count = row[1]
    loss_count = row[2]

    total = win_count + loss_count
    ratio = f"{win_count}/{total}" if total > 0 else "N/A"

    return f"{player_name}: {ratio}"
