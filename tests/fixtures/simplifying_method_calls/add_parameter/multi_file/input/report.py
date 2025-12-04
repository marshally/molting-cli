from calculator import Calculator


def generate_report():
    calc = Calculator()
    total = calc.calculate(10, 20)
    print(f"Total: {total}")
    return total


def daily_summary():
    calc = Calculator()
    morning = calc.calculate(5, 15)
    afternoon = calc.calculate(20, 30)
    return morning + afternoon
