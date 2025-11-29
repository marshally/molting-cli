"""Utility for inserting methods into class bodies at specific positions.

The MethodInserter transformer inserts a new method immediately after
a specified method in a class, rather than appending to the end of the
class body. This is useful for refactorings that extract methods and
want them positioned near related methods.
"""

import libcst as cst


class MethodInserter(cst.CSTTransformer):
    """Inserts a new method after a specified method in a class.

    This transformer finds a target method in a specific class and inserts
    a new method immediately after it. If the target method is the last
    method in the class, the new method is appended.

    Example:
        >>> code = '''
        >>> class Rectangle:
        >>>     def area(self):
        >>>         return self._width * self._height
        >>>     def diagonal(self):
        >>>         return (self._width**2 + self._height**2) ** 0.5
        >>> '''
        >>> module = cst.parse_module(code)
        >>> new_method = create_perimeter_method()  # Some function
        >>> inserter = MethodInserter("Rectangle", "area", new_method)
        >>> modified = module.visit(inserter)
        >>> # Now "perimeter" method is between "area" and "diagonal"
    """

    def __init__(
        self, class_name: str, target_method_name: str, new_method: cst.FunctionDef
    ) -> None:
        """Initialize the method inserter.

        Args:
            class_name: Name of the class where the method should be inserted
            target_method_name: Name of the method after which to insert
            new_method: The FunctionDef node to insert
        """
        self.class_name = class_name
        self.target_method_name = target_method_name
        self.new_method = new_method
        self._in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Track entry into target class."""
        if node.name.value == self.class_name:
            self._in_target_class = True
        return True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition, inserting the method if it's the target class."""
        if original_node.name.value == self.class_name:
            self._in_target_class = False

            # Find the target method and insert after it
            new_body = list(updated_node.body.body)
            insert_index = self._find_target_method_index(original_node)

            if insert_index is not None:
                # Insert after the target method
                new_body.insert(insert_index + 1, self.new_method)

                return updated_node.with_changes(
                    body=updated_node.body.with_changes(body=tuple(new_body))
                )

        return updated_node

    def _find_target_method_index(self, class_node: cst.ClassDef) -> int | None:
        """Find the index of the target method in the class body.

        Args:
            class_node: The ClassDef node to search

        Returns:
            The index of the target method, or None if not found
        """
        for i, stmt in enumerate(class_node.body.body):
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == self.target_method_name:
                return i
        return None
