"""Utilities for constructing common CST nodes.

This module provides utility functions to simplify the creation of common
LibCST node patterns used across multiple refactoring commands.
"""

import libcst as cst


def create_super_init_call(args: list[cst.Arg] | None = None) -> cst.SimpleStatementLine:
    """Create a super().__init__() call statement.

    Args:
        args: Optional list of arguments to pass to super().__init__()

    Returns:
        A SimpleStatementLine containing the super().__init__() call

    Examples:
        >>> # Create super().__init__() with no arguments
        >>> stmt = create_super_init_call()
        >>> print(stmt)  # super().__init__()

        >>> # Create super().__init__(name, age)
        >>> args = [cst.Arg(value=cst.Name("name")), cst.Arg(value=cst.Name("age"))]
        >>> stmt = create_super_init_call(args)
        >>> print(stmt)  # super().__init__(name, age)
    """
    call_args = args if args is not None else []

    super_call = cst.Expr(
        value=cst.Call(
            func=cst.Attribute(
                value=cst.Call(func=cst.Name("super"), args=[]),
                attr=cst.Name("__init__"),
            ),
            args=call_args,
        )
    )

    return cst.SimpleStatementLine(body=[super_call])


def create_field_assignment(
    field_name: str, value: cst.BaseExpression | None = None
) -> cst.SimpleStatementLine:
    """Create a self.field = value assignment statement.

    Args:
        field_name: The name of the field to assign to (without 'self.' prefix)
        value: The expression to assign. Defaults to cst.Name(field_name)

    Returns:
        A SimpleStatementLine containing the assignment

    Examples:
        >>> # Create self.name = name
        >>> stmt = create_field_assignment("name")
        >>> print(stmt)  # self.name = name

        >>> # Create self.age = 0
        >>> stmt = create_field_assignment("age", cst.Integer("0"))
        >>> print(stmt)  # self.age = 0
    """
    if value is None:
        value = cst.Name(field_name)

    assignment = cst.Assign(
        targets=[
            cst.AssignTarget(
                target=cst.Attribute(value=cst.Name("self"), attr=cst.Name(field_name))
            )
        ],
        value=value,
    )

    return cst.SimpleStatementLine(body=[assignment])


def create_init_method(
    params: list[str],
    field_assignments: dict[str, cst.BaseExpression] | None = None,
    super_call_args: list[cst.Arg] | None = None,
) -> cst.FunctionDef:
    """Create an __init__ method with parameters and field assignments.

    Args:
        params: List of parameter names (not including 'self')
        field_assignments: Optional dict mapping field names to their value expressions.
                          If None, creates self.param = param for each parameter.
        super_call_args: Optional list of arguments for super().__init__() call.
                        If provided, super().__init__() is called before field assignments.

    Returns:
        A FunctionDef for the __init__ method

    Examples:
        >>> # Create simple __init__(self, name, age) with field assignments
        >>> method = create_init_method(["name", "age"])
        >>> # Produces:
        >>> # def __init__(self, name, age):
        >>> #     self.name = name
        >>> #     self.age = age

        >>> # Create __init__ with super() call
        >>> super_args = [cst.Arg(value=cst.Name("name"))]
        >>> method = create_init_method(["name", "age"], super_call_args=super_args)
        >>> # Produces:
        >>> # def __init__(self, name, age):
        >>> #     super().__init__(name)
        >>> #     self.name = name
        >>> #     self.age = age

        >>> # Create __init__ with custom field values
        >>> field_vals = {"count": cst.Integer("0")}
        >>> method = create_init_method(["name"], field_assignments=field_vals)
        >>> # Produces:
        >>> # def __init__(self, name):
        >>> #     self.count = 0
    """
    # Build parameter list with self
    param_list = [cst.Param(name=cst.Name("self"))]
    for param_name in params:
        param_list.append(cst.Param(name=cst.Name(param_name)))

    # Build body statements
    body_stmts: list[cst.BaseStatement] = []

    # Add super().__init__() call if requested
    if super_call_args is not None:
        body_stmts.append(create_super_init_call(super_call_args))

    # Add field assignments
    if field_assignments is None:
        # Default: create self.param = param for each parameter
        for param_name in params:
            body_stmts.append(create_field_assignment(param_name))
    else:
        # Use provided field assignments
        for field_name, value in field_assignments.items():
            body_stmts.append(create_field_assignment(field_name, value))

    return cst.FunctionDef(
        name=cst.Name("__init__"),
        params=cst.Parameters(params=param_list),
        body=cst.IndentedBlock(body=tuple(body_stmts)),
    )


def create_parameter(
    name: str,
    annotation: cst.Annotation | None = None,
    default: cst.BaseExpression | None = None,
) -> cst.Param:
    """Create a function parameter with optional annotation and default value.

    Args:
        name: The parameter name
        annotation: Optional type annotation
        default: Optional default value expression

    Returns:
        A Param node for use in function definitions

    Examples:
        >>> # Create simple parameter: name
        >>> param = create_parameter("name")

        >>> # Create parameter with annotation: name: str
        >>> param = create_parameter("name", cst.Annotation(annotation=cst.Name("str")))

        >>> # Create parameter with default: count=0
        >>> param = create_parameter("count", default=cst.Integer("0"))

        >>> # Create parameter with annotation and default: age: int = 0
        >>> param = create_parameter(
        ...     "age",
        ...     annotation=cst.Annotation(annotation=cst.Name("int")),
        ...     default=cst.Integer("0")
        ... )
    """
    return cst.Param(name=cst.Name(name), annotation=annotation, default=default)
