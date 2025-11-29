"""Tests for MethodInserter utility.

Tests for the MethodInserter helper that inserts methods into a class
immediately after a specified method name, rather than at the end of
the class body.
"""

import libcst as cst

from molting.core.method_inserter import MethodInserter


class TestMethodInserter:
    """Tests for MethodInserter utility."""

    def test_inserts_method_after_target_method(self) -> None:
        """Should insert new method immediately after the target method."""
        code = """
class Rectangle:
    def area(self):
        return self._width * self._height

    def diagonal(self):
        return (self._width**2 + self._height**2) ** 0.5
"""
        module = cst.parse_module(code)

        # Create a new method to insert
        new_method = cst.FunctionDef(
            name=cst.Name("perimeter"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Integer("0")
                            )
                        ]
                    )
                ]
            ),
        )

        # Insert the method after "area"
        inserter = MethodInserter("Rectangle", "area", new_method)
        modified = module.visit(inserter)

        # Verify the method was inserted
        code_result = modified.code

        # The perimeter method should come after area and before diagonal
        area_pos = code_result.find("def area(self):")
        perimeter_pos = code_result.find("def perimeter(self):")
        diagonal_pos = code_result.find("def diagonal(self):")

        assert area_pos < perimeter_pos < diagonal_pos

    def test_inserts_method_when_target_is_last_method(self) -> None:
        """Should insert method even when target is the last method."""
        code = """
class Rectangle:
    def area(self):
        return self._width * self._height
"""
        module = cst.parse_module(code)

        # Create a new method to insert
        new_method = cst.FunctionDef(
            name=cst.Name("perimeter"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Integer("0")
                            )
                        ]
                    )
                ]
            ),
        )

        # Insert the method after "area" (which is the last method)
        inserter = MethodInserter("Rectangle", "area", new_method)
        modified = module.visit(inserter)

        # Verify the method was inserted
        code_result = modified.code
        assert "def perimeter(self):" in code_result

    def test_ignores_insertion_if_method_not_found(self) -> None:
        """Should not insert method if target method is not found."""
        code = """
class Rectangle:
    def area(self):
        return self._width * self._height
"""
        module = cst.parse_module(code)

        # Create a new method to insert
        new_method = cst.FunctionDef(
            name=cst.Name("perimeter"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Integer("0")
                            )
                        ]
                    )
                ]
            ),
        )

        # Try to insert after non-existent method "perimeter"
        inserter = MethodInserter("Rectangle", "perimeter", new_method)
        modified = module.visit(inserter)

        # Original code should be unchanged
        code_result = modified.code
        original_method_count = code_result.count("def ")
        assert original_method_count == 1  # Still just the area method

    def test_inserts_method_in_correct_class_only(self) -> None:
        """Should insert method only in the specified class."""
        code = """
class Rectangle:
    def area(self):
        return self._width * self._height

class Circle:
    def area(self):
        return 3.14159 * self._radius ** 2
"""
        module = cst.parse_module(code)

        # Create a new method to insert
        new_method = cst.FunctionDef(
            name=cst.Name("perimeter"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Integer("0")
                            )
                        ]
                    )
                ]
            ),
        )

        # Insert the method after area in Rectangle
        inserter = MethodInserter("Rectangle", "area", new_method)
        modified = module.visit(inserter)

        # Verify the method was inserted in Rectangle but not Circle
        code_result = modified.code

        # Count method definitions
        method_count = code_result.count("def ")
        assert method_count == 3  # area (Rectangle), area (Circle), perimeter (Rectangle)

        # Verify that perimeter is in Rectangle section
        rectangle_section = code_result.split("class Circle:")[0]
        assert "def perimeter(self):" in rectangle_section

    def test_preserves_class_with_other_statements(self) -> None:
        """Should preserve class attributes and other statements."""
        code = """
class Rectangle:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    def area(self):
        return self._width * self._height
"""
        module = cst.parse_module(code)

        # Create a new method to insert
        new_method = cst.FunctionDef(
            name=cst.Name("perimeter"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Integer("0")
                            )
                        ]
                    )
                ]
            ),
        )

        # Insert the method after area
        inserter = MethodInserter("Rectangle", "area", new_method)
        modified = module.visit(inserter)

        # Verify structure is preserved
        code_result = modified.code
        assert "def __init__" in code_result
        assert "self._width = width" in code_result
        assert "def area(self):" in code_result
        assert "def perimeter(self):" in code_result
