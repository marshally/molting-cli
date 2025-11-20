class Calculator:
    """A simple calculator class."""

    def calculate_sum(self, a, b):
        """Add two numbers together."""
        return a + b

    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b


calc = Calculator()
result = calc.calculate_sum(5, 3)
print(result)
