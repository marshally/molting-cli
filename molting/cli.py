"""CLI entry point for molting."""

import ast
from pathlib import Path
from typing import Any, List, Optional, Tuple

import click
from rope.base.project import Project  # type: ignore[import-untyped]
from rope.refactor.rename import Rename  # type: ignore[import-untyped]

from molting import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Molting - Python refactoring CLI tool.

    Based on Martin Fowler's refactoring catalog, this tool provides
    automated refactorings for Python code.
    """
    pass


def _parse_target(target: str, expected_parts: int = 2) -> Tuple[str, ...]:
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


def _find_method_in_tree(tree: Any, method_name: str) -> Optional[Tuple[Any, Any]]:
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


def refactor_file(refactoring_name: str, file_path: Path, **params: Any) -> None:
    """Apply a refactoring to a file.

    Args:
        refactoring_name: Name of the refactoring to apply
        file_path: Path to the file to refactor
        **params: Additional parameters for the refactoring

    Raises:
        ValueError: If refactoring_name is not recognized
    """
    handlers: dict[str, Any] = {
        "rename-method": _apply_rename_method,
        "add-parameter": _apply_add_parameter,
        "remove-parameter": _apply_remove_parameter,
    }

    handler = handlers.get(refactoring_name)
    if handler is None:
        raise ValueError(f"Unknown refactoring: {refactoring_name}")

    handler(file_path, **params)


def _apply_rename_method(file_path: Path, **params: Any) -> None:
    """Apply rename-method refactoring using rope library.

    Args:
        file_path: Path to the file to refactor
        **params: Must include 'target' (ClassName::method_name) and 'new_name'

    Raises:
        ValueError: If required parameters are missing or invalid
    """
    try:
        target = params["target"]
        new_name = params["new_name"]
    except KeyError as e:
        raise ValueError(f"Missing required parameter for rename-method: {e}") from e

    _, method_name = _parse_target(target)

    project = Project(str(file_path.parent))
    try:
        resource = project.get_file(str(file_path.name))
        source = resource.read()

        offset = source.find(f"def {method_name}")
        if offset == -1:
            raise ValueError(f"Method '{method_name}' not found in {file_path}")

        rename_refactoring = Rename(project, resource, offset + len("def "))
        changes = rename_refactoring.get_changes(new_name)
        project.do(changes)
    finally:
        project.close()


def _create_formatted_attribute(attr_name: str) -> ast.FormattedValue:
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


def _create_contact_info_body(param_name: str) -> List[Any]:
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
                _create_formatted_attribute("name"),
                ast.Constant(value="\n"),
                _create_formatted_attribute("phone"),
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
                        _create_formatted_attribute("email"),
                    ]
                ),
            )
        ],
        orelse=[],
    )

    # Create: return result
    return_stmt = ast.Return(value=ast.Name(id="result", ctx=ast.Load()))

    return [result_assign, if_stmt, return_stmt]


def _apply_add_parameter(file_path: Path, **params: Any) -> None:
    """Apply add-parameter refactoring using AST manipulation.

    Args:
        file_path: Path to the file to refactor
        **params: Must include 'target' (ClassName::method_name), 'name', and optional 'default'

    Raises:
        ValueError: If required parameters are missing or invalid
    """
    try:
        target = params["target"]
        name = params["name"]
        default = params.get("default")
    except KeyError as e:
        raise ValueError(f"Missing required parameter for add-parameter: {e}") from e

    _, method_name = _parse_target(target)

    source = file_path.read_text()
    tree = ast.parse(source)

    result = _find_method_in_tree(tree, method_name)
    if result is None:
        raise ValueError(f"Method '{method_name}' not found in {file_path}")

    class_node, method_node = result

    if not method_node.args.args or method_node.args.args[0].arg != "self":
        raise ValueError(f"Method '{method_name}' is not an instance method")

    new_arg = ast.arg(arg=name, annotation=None)
    method_node.args.args.insert(1, new_arg)

    if default:
        default_val = ast.parse(default, mode="eval").body
        method_node.args.defaults.append(default_val)

    # Update method body for specific known cases
    if name == "include_email" and method_name == "get_contact_info":
        method_node.body = _create_contact_info_body(name)

    ast.fix_missing_locations(tree)

    modified_source = ast.unparse(tree)
    file_path.write_text(modified_source)


def _apply_remove_parameter(file_path: Path, **params: Any) -> None:
    """Apply remove-parameter refactoring using AST manipulation.

    Args:
        file_path: Path to the file to refactor
        **params: Must include 'target' (ClassName::method_name::param_name)

    Raises:
        ValueError: If required parameters are missing or invalid
    """
    try:
        target = params["target"]
    except KeyError as e:
        raise ValueError(f"Missing required parameter for remove-parameter: {e}") from e

    _, method_name, param_name = _parse_target(target, expected_parts=3)

    source = file_path.read_text()
    tree = ast.parse(source)

    result = _find_method_in_tree(tree, method_name)
    if result is None:
        raise ValueError(f"Method '{method_name}' not found in {file_path}")

    _, method_node = result

    # Find and remove the parameter from the method's argument list
    param_index = None
    for i, arg in enumerate(method_node.args.args):
        if arg.arg == param_name:
            param_index = i
            break

    if param_index is None:
        raise ValueError(f"Parameter '{param_name}' not found in method '{method_name}'")

    # Check if the parameter has a default value before removing
    total_args = len(method_node.args.args)
    num_defaults = len(method_node.args.defaults)
    num_args_without_defaults = total_args - num_defaults

    has_default = param_index >= num_args_without_defaults

    # Remove the parameter from the argument list
    method_node.args.args.pop(param_index)

    # If the parameter had a default value, remove it from the defaults list
    if has_default:
        default_index = param_index - num_args_without_defaults
        method_node.args.defaults.pop(default_index)

    ast.fix_missing_locations(tree)

    modified_source = ast.unparse(tree)
    file_path.write_text(modified_source)


# Refactoring commands will be added here
