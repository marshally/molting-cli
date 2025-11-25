"""Change Reference to Value refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import extract_all_methods, find_class_in_module
from molting.core.code_generation_utils import create_parameter


class ChangeReferenceToValueCommand(BaseCommand):
    """Command to change a reference object into a value object."""

    name = "change-reference-to-value"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for change-reference-to-value: 'target'")

    def execute(self) -> None:
        """Apply change-reference-to-value refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ChangeReferenceToValueTransformer(target_class)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ChangeReferenceToValueTransformer(cst.CSTTransformer):
    """Transforms a reference object into a value object."""

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
        methods = extract_all_methods(class_def, exclude_init=False)
        for method in methods:
            if method.name.value == "__init__":
                # Get the first parameter after 'self'
                params = method.params.params
                if len(params) > 1:
                    self.init_param_name = params[1].name.value
                break

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Remove _instances and factory method, add __eq__ and __hash__.

        Args:
            original_node: The original class node
            updated_node: The updated class node

        Returns:
            Modified class definition
        """
        if updated_node.name.value != self.target_class:
            return updated_node

        # Filter out _instances assignment and factory method
        new_body: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            # Skip _instances assignment
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) > 0 and isinstance(stmt.body[0], cst.Assign):
                    assign = stmt.body[0]
                    if len(assign.targets) > 0:
                        target = assign.targets[0].target
                        if isinstance(target, cst.Name) and target.value == "_instances":
                            continue

            # Skip factory method (classmethod with @classmethod decorator)
            if isinstance(stmt, cst.FunctionDef):
                has_classmethod = any(
                    isinstance(dec.decorator, cst.Name) and dec.decorator.value == "classmethod"
                    for dec in stmt.decorators
                )
                if has_classmethod:
                    continue

            new_body.append(stmt)

        # Add __eq__ method
        param_name = self.init_param_name or "code"
        eq_method = self._create_eq_method(param_name)
        new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
        new_body.append(eq_method)

        # Add __hash__ method
        hash_method = self._create_hash_method(param_name)
        new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
        new_body.append(hash_method)

        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_eq_method(self, param_name: str) -> cst.FunctionDef:
        """Create the __eq__ method for value-based equality.

        Args:
            param_name: The parameter name from __init__

        Returns:
            The __eq__ method definition
        """
        return cst.FunctionDef(
            name=cst.Name("__eq__"),
            params=cst.Parameters(
                params=[
                    create_parameter("self"),
                    create_parameter("other"),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    # if not isinstance(other, Currency):
                    cst.If(
                        test=cst.UnaryOperation(
                            operator=cst.Not(),
                            expression=cst.Call(
                                func=cst.Name("isinstance"),
                                args=[
                                    cst.Arg(value=cst.Name("other")),
                                    cst.Arg(value=cst.Name(self.target_class)),
                                ],
                            ),
                        ),
                        body=cst.IndentedBlock(
                            body=[
                                cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("False"))])
                            ]
                        ),
                    ),
                    # return self.code == other.code
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Comparison(
                                    left=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(param_name),
                                    ),
                                    comparisons=[
                                        cst.ComparisonTarget(
                                            operator=cst.Equal(),
                                            comparator=cst.Attribute(
                                                value=cst.Name("other"),
                                                attr=cst.Name(param_name),
                                            ),
                                        )
                                    ],
                                )
                            )
                        ]
                    ),
                ]
            ),
        )

    def _create_hash_method(self, param_name: str) -> cst.FunctionDef:
        """Create the __hash__ method for value objects.

        Args:
            param_name: The parameter name from __init__

        Returns:
            The __hash__ method definition
        """
        return cst.FunctionDef(
            name=cst.Name("__hash__"),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(
                body=[
                    # return hash(self.code)
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Call(
                                    func=cst.Name("hash"),
                                    args=[
                                        cst.Arg(
                                            value=cst.Attribute(
                                                value=cst.Name("self"),
                                                attr=cst.Name(param_name),
                                            )
                                        )
                                    ],
                                )
                            )
                        ]
                    )
                ]
            ),
        )


# Register the command
register_command(ChangeReferenceToValueCommand)
