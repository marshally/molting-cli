"""Example code for replace-temp-with-query with decorators."""


class Rectangle:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    @property
    def area(self):
        """Calculate the area of the rectangle."""
        if self.perimeter() > 100:
            return self._width * self._height * 0.9
        return self._width * self._height

    def perimeter(self):
        return 2 * (self._width + self._height)

    @property
    def diagonal(self):
        """Calculate the diagonal of the rectangle."""
        return (self._width**2 + self._height**2) ** 0.5
