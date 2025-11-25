"""Change Value to Reference refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module
from molting.core.code_generation_utils import create_parameter


class ChangeValueToReferenceCommand(BaseCommand):
    """Command to change a value object into a reference object."""

    name = "change-value-to-reference"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for change-value-to-reference: 'target'")

    def execute(self) -> None:
        """Apply change-value-to-reference refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ChangeValueToReferenceTransformer(target_class)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ChangeValueToReferenceTransformer(cst.CSTTransformer):
    """Transforms a value object into a reference object."""

    def __init__(self, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to transform
        """
        self.target_class = target_class
        self.init_param_name: str | None = None

    def visit_Module(self, node: cst.Module) -> bool:  # noqa: N802
        """Visit module to extract parameter name from target class __init__.

        Args:
            node: The module node

        Returns:
            True to continue visiting
        """
        target_class_def = find_class_in_module(node, self.target_class)
        if target_class_def:
            self._extract_init_param(target_class_def)
        return True

    def _extract_init_param(self, class_def: cst.ClassDef) -> None:
        """Extract the parameter name from __init__.

        Args:
            class_def: The class definition
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Get the first parameter after 'self'
                params = stmt.params.params
                if len(params) > 1:
                    self.init_param_name = params[1].name.value
                break

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Transform Customer(name) to Customer.get_named(name).

        Args:
            original_node: The original call node
            updated_node: The updated call node

        Returns:
            Transformed call node
        """
        if isinstance(updated_node.func, cst.Name):
            if updated_node.func.value == self.target_class:
                # Replace Customer(name) with Customer.get_named(name)
                return updated_node.with_changes(
                    func=cst.Attribute(
                        value=cst.Name(self.target_class),
                        attr=cst.Name("get_named"),
                    )
                )
        return updated_node

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Add _instances and get_named to the target class.

        Args:
            original_node: The original class node
            updated_node: The updated class node

        Returns:
            Modified class definition
        """
        if updated_node.name.value != self.target_class:
            return updated_node

        # Add _instances class variable and get_named method
        new_body: list[cst.BaseStatement] = []

        # Add _instances = {} as first item
        instances_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("_instances"))],
                    value=cst.Dict(elements=[]),
                )
            ]
        )
        new_body.append(instances_assignment)

        # Add empty line
        new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))

        # Add existing body
        new_body.extend(updated_node.body.body)

        # Add empty line before get_named
        new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))

        # Add get_named classmethod
        param_name = self.init_param_name or "name"
        get_named_method = self._create_get_named_method(param_name)
        new_body.append(get_named_method)

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_get_named_method(self, param_name: str) -> cst.FunctionDef:
        """Create the get_named classmethod.

        Args:
            param_name: The parameter name from __init__

        Returns:
            The get_named classmethod definition
        """
        return cst.FunctionDef(
            name=cst.Name("get_named"),
            params=cst.Parameters(
                params=[
                    create_parameter("cls"),
                    create_parameter(param_name),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.If(
                        test=cst.Comparison(
                            left=cst.Name(param_name),
                            comparisons=[
                                cst.ComparisonTarget(
                                    operator=cst.NotIn(),
                                    comparator=cst.Attribute(
                                        value=cst.Name("cls"),
                                        attr=cst.Name("_instances"),
                                    ),
                                )
                            ],
                        ),
                        body=cst.IndentedBlock(
                            body=[
                                cst.SimpleStatementLine(
                                    body=[
                                        cst.Assign(
                                            targets=[
                                                cst.AssignTarget(
                                                    target=cst.Subscript(
                                                        value=cst.Attribute(
                                                            value=cst.Name("cls"),
                                                            attr=cst.Name("_instances"),
                                                        ),
                                                        slice=[
                                                            cst.SubscriptElement(
                                                                slice=cst.Index(
                                                                    value=cst.Name(param_name)
                                                                )
                                                            )
                                                        ],
                                                    )
                                                )
                                            ],
                                            value=cst.Call(
                                                func=cst.Name(self.target_class),
                                                args=[cst.Arg(value=cst.Name(param_name))],
                                            ),
                                        )
                                    ]
                                )
                            ]
                        ),
                    ),
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Subscript(
                                    value=cst.Attribute(
                                        value=cst.Name("cls"),
                                        attr=cst.Name("_instances"),
                                    ),
                                    slice=[
                                        cst.SubscriptElement(
                                            slice=cst.Index(value=cst.Name(param_name))
                                        )
                                    ],
                                )
                            )
                        ]
                    ),
                ]
            ),
            decorators=[cst.Decorator(decorator=cst.Name("classmethod"))],
        )


# Register the command
register_command(ChangeValueToReferenceCommand)
