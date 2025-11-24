"""Shared AST utility functions for refactorings."""

import ast
from typing import Any, List, Optional, Sequence, Tuple

import libcst as cst

# Target format constants for line number parsing
TARGET_SEPARATOR = "#"
LINE_PREFIX = "L"
LINE_RANGE_SEPARATOR = "-"


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


def parse_line_number(line_spec: str) -> int:
    """Parse line number from 'L4' format.

    Args:
        line_spec: Line specification in format 'L4'

    Returns:
        Line number as integer

    Raises:
        ValueError: If line specification format is invalid
    """
    if not line_spec.startswith(LINE_PREFIX):
        raise ValueError(f"Invalid line format '{line_spec}'. Expected 'L' prefix")

    try:
        line_number = int(line_spec[len(LINE_PREFIX) :])
    except ValueError as e:
        raise ValueError(f"Invalid line number in '{line_spec}': {e}") from e

    if line_number < 0:
        raise ValueError(f"Invalid line number in '{line_spec}': line numbers cannot be negative")

    return line_number


def parse_line_range(line_range: str) -> Tuple[int, int]:
    """Parse line range from 'L9-L11' format.

    Args:
        line_range: Line range in format 'L9-L11'

    Returns:
        Tuple of (start_line, end_line)

    Raises:
        ValueError: If line range format is invalid
    """
    if not line_range.startswith(LINE_PREFIX):
        raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L<start>-L<end>'")

    if LINE_RANGE_SEPARATOR not in line_range:
        raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L<start>-L<end>'")

    parts = line_range.split(LINE_RANGE_SEPARATOR)
    if len(parts) != 2:
        raise ValueError(f"Invalid line range format '{line_range}'. Expected 'L<start>-L<end>'")

    try:
        start_line = parse_line_number(parts[0])
        end_line = parse_line_number(parts[1])
    except ValueError as e:
        raise ValueError(f"Invalid line numbers in '{line_range}': {e}") from e

    return (start_line, end_line)


def _parse_class_method_part(class_method: str) -> Tuple[str, str]:
    """Parse the class::method portion of a target specification.

    Args:
        class_method: String in format 'ClassName::method' or 'function'

    Returns:
        Tuple of (class_or_function_name, method_name)
        For function-level targets, method_name will be empty string

    Raises:
        ValueError: If class::method format is invalid
    """
    if "::" in class_method:
        class_parts = class_method.split("::")
        if len(class_parts) == 2:
            return (class_parts[0], class_parts[1])
        else:
            raise ValueError(f"Invalid class::method format in '{class_method}'")
    else:
        # Function-level target
        return (class_method, "")


def parse_target_with_line(target: str) -> Tuple[str, str, str]:
    """Parse target with line number from 'ClassName::method#L4' format.

    Args:
        target: Target string in format 'ClassName::method#L4' or 'function#L4'

    Returns:
        Tuple of (class_or_function_name, method_name, line_spec)
        For function-level targets, method_name will be empty string

    Raises:
        ValueError: If target format is invalid
    """
    parts = target.split(TARGET_SEPARATOR)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid target format '{target}'. "
            f"Expected 'ClassName::method#L<line>' or 'function#L<line>'"
        )

    class_method = parts[0]
    line_spec = parts[1]

    # Validate line specification
    parse_line_number(line_spec)

    # Parse class and method name
    class_name, method_name = _parse_class_method_part(class_method)
    return (class_name, method_name, line_spec)


def parse_target_with_range(target: str) -> Tuple[str, str, int, int]:
    """Parse target with line range from 'ClassName::method#L9-L11' format.

    Args:
        target: Target string in format 'ClassName::method#L9-L11' or 'function#L9-L11'

    Returns:
        Tuple of (class_or_function_name, method_name, start_line, end_line)
        For function-level targets, method_name will be empty string

    Raises:
        ValueError: If target format is invalid
    """
    parts = target.split(TARGET_SEPARATOR)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid target format '{target}'. "
            f"Expected 'ClassName::method#L<start>-L<end>' or 'function#L<start>-L<end>'"
        )

    class_method = parts[0]
    line_range_spec = parts[1]

    # Parse line range
    start_line, end_line = parse_line_range(line_range_spec)

    # Parse class and method name
    class_name, method_name = _parse_class_method_part(class_method)
    return (class_name, method_name, start_line, end_line)


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


def extract_init_field_assignments(
    init_method: cst.FunctionDef,
) -> dict[str, cst.BaseExpression]:
    """Extract self.field = value assignments from __init__ method.

    Args:
        init_method: The __init__ method to analyze

    Returns:
        Dictionary mapping field names to their assigned values
    """
    field_assignments: dict[str, cst.BaseExpression] = {}

    if not isinstance(init_method.body, cst.IndentedBlock):
        return field_assignments

    for stmt in init_method.body.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            result = find_self_field_assignment(stmt)
            if result:
                field_name, value = result
                field_assignments[field_name] = value

    return field_assignments


def find_self_field_assignment(
    stmt: cst.SimpleStatementLine,
) -> tuple[str, cst.BaseExpression] | None:
    """Extract (field_name, value) if statement is self.field = value.

    Args:
        stmt: The statement to check

    Returns:
        Tuple of (field_name, value) or None if not a self.field assignment
    """
    if not isinstance(stmt, cst.SimpleStatementLine):
        return None

    for item in stmt.body:
        if isinstance(item, cst.Assign):
            for target in item.targets:
                if isinstance(target.target, cst.Attribute):
                    if (
                        isinstance(target.target.value, cst.Name)
                        and target.target.value.value == "self"
                    ):
                        field_name = target.target.attr.value
                        return (field_name, item.value)

    return None


def is_assignment_to_field(stmt: cst.BaseStatement, field_names: set[str]) -> bool:
    """Check if statement assigns to any of the specified fields.

    Args:
        stmt: The statement to check
        field_names: Set of field names to check for

    Returns:
        True if statement assigns to one of the fields
    """
    if isinstance(stmt, cst.SimpleStatementLine):
        for item in stmt.body:
            if isinstance(item, cst.Assign):
                for target in item.targets:
                    if isinstance(target.target, cst.Attribute):
                        if isinstance(target.target.value, cst.Name):
                            if target.target.value.value == "self":
                                if target.target.attr.value in field_names:
                                    return True
    return False


def find_class_in_module(module: cst.Module, class_name: str) -> cst.ClassDef | None:
    """Find a class definition by name in a module.

    Args:
        module: The module to search
        class_name: Name of the class to find

    Returns:
        The class definition node, or None if not found
    """
    for stmt in module.body:
        if isinstance(stmt, cst.ClassDef) and stmt.name.value == class_name:
            return stmt
    return None


def find_method_in_class(class_def: cst.ClassDef, method_name: str) -> cst.FunctionDef | None:
    """Find a method in a class definition.

    Args:
        class_def: The class definition to search
        method_name: Name of the method to find

    Returns:
        The method definition node, or None if not found
    """
    if not isinstance(class_def.body, cst.IndentedBlock):
        return None

    for stmt in class_def.body.body:
        if isinstance(stmt, cst.FunctionDef) and stmt.name.value == method_name:
            return stmt
    return None


def extract_all_methods(
    class_def: cst.ClassDef, exclude_init: bool = False
) -> list[cst.FunctionDef]:
    """Extract all method definitions from a class.

    Args:
        class_def: The class definition to extract methods from
        exclude_init: If True, exclude __init__ method from results

    Returns:
        List of method definition nodes
    """
    methods: list[cst.FunctionDef] = []

    if not isinstance(class_def.body, cst.IndentedBlock):
        return methods

    for stmt in class_def.body.body:
        if isinstance(stmt, cst.FunctionDef):
            if exclude_init and stmt.name.value == "__init__":
                continue
            methods.append(stmt)

    return methods


def parse_comma_separated_list(value: str) -> list[str]:
    """Parse comma-separated string into list of trimmed values.

    Args:
        value: Comma-separated string

    Returns:
        List of trimmed string values
    """
    return [item.strip() for item in value.split(",")]


def is_pass_statement(stmt: cst.BaseStatement) -> bool:
    """Check if a statement is a pass statement.

    Args:
        stmt: The statement to check

    Returns:
        True if the statement is a pass statement
    """
    if isinstance(stmt, cst.SimpleStatementLine):
        if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Pass):
            return True
    return False


def is_empty_class(class_def: cst.ClassDef) -> bool:
    """Check if a class is empty (contains only pass or no statements).

    Args:
        class_def: The class definition to check

    Returns:
        True if the class contains only pass statements or is empty
    """
    if isinstance(class_def.body, cst.IndentedBlock):
        # Check if body contains only pass or empty statements
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this line only contains 'pass'
                if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Pass):
                    continue
                else:
                    # SimpleStatementLine with non-pass content means not empty
                    return False
            else:
                # Any other statement means it's not empty
                return False
        return True
    return True


def statements_contain_only_pass(stmts: Sequence[cst.BaseStatement]) -> bool:
    """Check if a list of statements contains only pass statements.

    Args:
        stmts: List of statements to check

    Returns:
        True if all statements are pass statements or list is empty
    """
    if not stmts:
        return True

    for stmt in stmts:
        if not is_pass_statement(stmt):
            return False
    return True
