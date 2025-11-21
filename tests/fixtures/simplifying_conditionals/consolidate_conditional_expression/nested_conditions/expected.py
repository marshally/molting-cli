def process_data(x, y, z):
    if x < 0 or y < 0 or z < 0:
        return None
    return x + y + z
