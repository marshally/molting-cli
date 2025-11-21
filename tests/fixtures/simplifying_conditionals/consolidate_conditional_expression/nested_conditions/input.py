def process_data(x, y, z):
    if x < 0:
        return None
    if y < 0:
        return None
    if z < 0:
        return None
    return x + y + z
