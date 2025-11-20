def calculate(x, y, z):
    assert x > 0 and y < 100, "x must be positive and y must be less than 100"
    result = x + y * z
    return result
