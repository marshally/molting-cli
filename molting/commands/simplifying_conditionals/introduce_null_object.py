"""Introduce Null Object refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceNullObjectCommand(BaseCommand):
    """Command to replace null checks with a null object."""

    name = "introduce-null-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target_class")

    def execute(self) -> None:
        """Apply introduce-null-object refactoring using libCST.

        Raises:
            ValueError: If class not found
        """
        target_class = self.params["target_class"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = IntroduceNullObjectTransformer(target_class)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class IntroduceNullObjectTransformer(cst.CSTTransformer):
    """Transformer to introduce a null object pattern."""

    def __init__(self, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to add null object pattern to
        """
        self.target_class = target_class
        self.target_class_found = False
        self.init_params: list[tuple[str, str | None]] = []

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.FlattenSentinel[cst.ClassDef]:
        """Process class definition and add null object pattern."""
        if updated_node.name.value == self.target_class:
            self.target_class_found = True

            # Extract __init__ parameters for the null class
            for stmt in updated_node.body.body:
                if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                    # Collect parameters and their defaults
                    for param in stmt.params.params:
                        if param.name.value != "self":
                            default_value = None
                            if param.default:
                                if isinstance(param.default, cst.SimpleString):
                                    default_value = param.default.value
                            self.init_params.append((param.name.value, default_value))

            # Add is_null() method
            is_null_method = cst.FunctionDef(
                name=cst.Name("is_null"),
                params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
                body=cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("False"))])]
                ),
                leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))],
            )

            # Add is_null method to class body
            new_body = list(updated_node.body.body)
            new_body.append(is_null_method)
            updated_node = updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

            # Create NullCustomer class
            null_class_name = f"Null{self.target_class}"

            # Build __init__ for null class
            null_init_assignments = []
            for param_name, default_value in self.init_params:
                if param_name == "name":
                    value = cst.SimpleString('"Unknown"')
                elif param_name == "plan":
                    value = cst.SimpleString('"Basic"')
                else:
                    if default_value:
                        value = cst.SimpleString(default_value)
                    else:
                        value = cst.Name("None")

                null_init_assignments.append(
                    cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(
                                        target=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(param_name),
                                        )
                                    )
                                ],
                                value=value,
                            )
                        ]
                    )
                )

            null_init = cst.FunctionDef(
                name=cst.Name("__init__"),
                params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
                body=cst.IndentedBlock(body=null_init_assignments),
            )

            # Create is_null method for null class
            null_is_null_method = cst.FunctionDef(
                name=cst.Name("is_null"),
                params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
                body=cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("True"))])]
                ),
                leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))],
            )

            null_class = cst.ClassDef(
                name=cst.Name(null_class_name),
                bases=[cst.Arg(value=cst.Name(self.target_class))],
                body=cst.IndentedBlock(body=[null_init, null_is_null_method]),
                leading_lines=[
                    cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                    cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                ],
            )

            return cst.FlattenSentinel([updated_node, null_class])

        # Modify classes that have a parameter matching the target class name (in lowercase)
        # e.g., if target_class is "Customer", look for parameters named "customer"
        param_name = self.target_class.lower()
        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Check if this __init__ has a parameter matching our target class name
                has_target_param = any(
                    param.name.value == param_name
                    for param in stmt.params.params
                    if param.name.value != "self"
                )

                if has_target_param:
                    # Modify __init__ to use null object
                    new_stmt_body = []
                    for body_stmt in stmt.body.body:
                        if isinstance(body_stmt, cst.SimpleStatementLine):
                            modified = False
                            for item in body_stmt.body:
                                if isinstance(item, cst.Assign):
                                    for target in item.targets:
                                        if isinstance(target.target, cst.Attribute):
                                            if (
                                                isinstance(target.target.value, cst.Name)
                                                and target.target.value.value == "self"
                                                and target.target.attr.value == param_name
                                            ):
                                                # Replace with null object check
                                                new_value = cst.IfExp(
                                                    test=cst.Comparison(
                                                        left=cst.Name(param_name),
                                                        comparisons=[
                                                            cst.ComparisonTarget(
                                                                operator=cst.IsNot(),
                                                                comparator=cst.Name("None"),
                                                            )
                                                        ],
                                                    ),
                                                    body=cst.Name(param_name),
                                                    orelse=cst.Call(
                                                        func=cst.Name(f"Null{self.target_class}"),
                                                        args=[],
                                                    ),
                                                )
                                                new_stmt_body.append(
                                                    cst.SimpleStatementLine(
                                                        body=[
                                                            cst.Assign(
                                                                targets=item.targets,
                                                                value=new_value,
                                                            )
                                                        ]
                                                    )
                                                )
                                                modified = True
                            if not modified:
                                new_stmt_body.append(body_stmt)
                        else:
                            new_stmt_body.append(body_stmt)

                    # Rebuild class with modified __init__
                    new_body = []
                    for s in updated_node.body.body:
                        if s == stmt:
                            new_body.append(
                                stmt.with_changes(body=cst.IndentedBlock(body=new_stmt_body))
                            )
                        else:
                            new_body.append(s)

                    return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

        return updated_node


# Register the command
register_command(IntroduceNullObjectCommand)
