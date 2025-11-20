def analyze_performance(row):
    name = row[0]
    wins = row[1]
    losses = row[2]
    return f"{name}: {wins}W-{losses}L"
