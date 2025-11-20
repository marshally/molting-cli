"""Code analysis utilities."""

from typing import List


def extract_function_names(source: str) -> List[str]:
    """Extract all function names from source code.

    Args:
        source: Python source code

    Returns:
        List of function names found in the source
    """
    import ast

    try:
        tree = ast.parse(source)
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    except SyntaxError:
        return []
