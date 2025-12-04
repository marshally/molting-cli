from calculator import Calculator


def compute_batch(calculator, values):
    results = []
    for a, b in values:
        result = calculator.calculate(a, b, 2)
        results.append(result)
    return results


def quick_add(calculator, x, y):
    return calculator.calculate(x, y, 2)
