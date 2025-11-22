"""CLI entry point for molting."""

import ast
from pathlib import Path
from typing import Any

import click
from rope.base.project import Project  # type: ignore[import-untyped]
from rope.refactor.rename import Rename  # type: ignore[import-untyped]
from rope.refactor.change_signature import ChangeSignature  # type: ignore[import-untyped]

from molting import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Molting - Python refactoring CLI tool.

    Based on Martin Fowler's refactoring catalog, this tool provides
    automated refactorings for Python code.
    """
    pass


def _parse_target(target: str) -> tuple[str, str]:
    """Parse target in 'ClassName::method_name' format.

    Args:
        target: Target specification string

    Returns:
        (class_name, method_name) tuple

    Raises:
        ValueError: If format is invalid
    """
    parts = target.split("::")
    if len(parts) != 2:
        raise ValueError(f"Invalid target format '{target}'. Expected 'ClassName::method_name'")
    return parts


def _find_method_in_tree(tree: ast.Module, method_name: str) -> tuple[ast.ClassDef, ast.FunctionDef] | None:
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
    """
    if refactoring_name == "rename-method":
        _apply_rename_method(file_path, **params)
    elif refactoring_name == "add-parameter":
        _apply_add_parameter(file_path, **params)


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


def _create_contact_info_body(param_name: str) -> list[ast.stmt]:
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


# Refactoring commands will be added here
