"""Shared AST utility functions for refactorings."""

import ast
from typing import Any, List, Optional, Tuple


def parse_target(target: str, expected_parts: int = 2) -> Tuple[str, ...]:
    """Parse target in 'ClassName::method_name' or 'ClassName::method_name::param' format.

    Args:
        target: Target specification string
        expected_parts: Number of parts expected (default: 2)

    Returns:
        Tuple of target parts

    Raises:
        ValueError: If format is invalid
    """
    parts = target.split("::")
    if len(parts) != expected_parts:
        raise ValueError(
            f"Invalid target format '{target}'. Expected {expected_parts} parts separated by '::'"
        )
    return tuple(parts)  # type: ignore[return-value]


def find_method_in_tree(tree: Any, method_name: str) -> Optional[Tuple[Any, Any]]:
    """Find a method in a class within the AST tree.

    Args:
        tree: AST module to search
        method_name: Name of method to find

    Returns:
        (class_node, method_node) tuple or None if not found
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return (node, item)
    return None


def parameter_has_default(param_index: int, total_args: int, num_defaults: int) -> bool:
    """Check if a parameter at given index has a default value.

    In Python's AST, default values are stored separately from argument names.
    Arguments without defaults come first, then arguments with defaults.
    This function determines if a parameter at the given index has a default.

    Args:
        param_index: Index of the parameter in the argument list
        total_args: Total number of arguments
        num_defaults: Number of arguments with default values

    Returns:
        True if the parameter has a default value, False otherwise
    """
    num_args_without_defaults = total_args - num_defaults
    return param_index >= num_args_without_defaults


def create_formatted_attribute(attr_name: str) -> ast.FormattedValue:
    """Create a formatted value node for an attribute reference in an f-string.

    Args:
        attr_name: Name of the attribute to reference

    Returns:
        FormattedValue AST node
    """
    return ast.FormattedValue(
        value=ast.Attribute(
            value=ast.Name(id="self", ctx=ast.Load()),
            attr=attr_name,
            ctx=ast.Load(),
        ),
        conversion=-1,
        format_spec=None,
    )


def create_contact_info_body(param_name: str) -> List[Any]:
    """Create method body for get_contact_info with conditional email inclusion.

    Args:
        param_name: Name of the boolean parameter controlling email inclusion

    Returns:
        List of AST statement nodes for the method body
    """
    # Create: result = f"{self.name}\n{self.phone}"
    result_assign = ast.Assign(
        targets=[ast.Name(id="result", ctx=ast.Store())],
        value=ast.JoinedStr(
            values=[
                create_formatted_attribute("name"),
                ast.Constant(value="\n"),
                create_formatted_attribute("phone"),
            ]
        ),
    )

    # Create: if <param_name>: result += f"\n{self.email}"
    if_stmt = ast.If(
        test=ast.Name(id=param_name, ctx=ast.Load()),
        body=[
            ast.AugAssign(
                target=ast.Name(id="result", ctx=ast.Store()),
                op=ast.Add(),
                value=ast.JoinedStr(
                    values=[
                        ast.Constant(value="\n"),
                        create_formatted_attribute("email"),
                    ]
                ),
            )
        ],
        orelse=[],
    )

    # Create: return result
    return_stmt = ast.Return(value=ast.Name(id="result", ctx=ast.Load()))

    return [result_assign, if_stmt, return_stmt]
