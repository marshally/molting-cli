class Calculator:
    """A simple calculator class."""

    def add_numbers(self, a, b):
        """Add two numbers together."""
        return a + b

    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b


calc = Calculator()
result = calc.add_numbers(5, 3)
print(result)
