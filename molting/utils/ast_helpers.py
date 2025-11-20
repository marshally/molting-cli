"""AST manipulation helper functions."""

import ast
from typing import Optional


def parse_source(source: str) -> Optional[ast.AST]:
    """Parse Python source code into an AST.

    Args:
        source: Python source code

    Returns:
        Parsed AST, or None if parsing fails
    """
    try:
        return ast.parse(source)
    except SyntaxError:
        return None
