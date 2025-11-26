"""Change Unidirectional Association to Bidirectional refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target
from molting.core.code_generation_utils import create_parameter

INIT_METHOD_NAME = "__init__"


class ChangeUnidirectionalAssociationToBidirectionalCommand(BaseCommand):
    """Command to change a unidirectional association to bidirectional."""

    name = "change-unidirectional-association-to-bidirectional"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "back")

    def execute(self) -> None:
        """Apply change-unidirectional-association-to-bidirectional refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        back_name = self.params["back"]

        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # Find the associated class - it should be the other class in the file
        class_finder = ClassFinderTransformer(class_name)
        module.visit(class_finder)

        if not class_finder.other_classes:
            raise ValueError(f"Could not find associated class for {class_name}")

        # Assume the first other class is the associated one
        associated_class_name = class_finder.other_classes[0]

        # Apply the transformation
        transformer = ChangeUnidirectionalToBidirectionalTransformer(
            source_class_name=class_name,
            field_name=field_name,
            target_class_name=associated_class_name,
            back_reference_name=back_name,
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ClassFinderTransformer(cst.CSTVisitor):
    """Find all classes in a module except the source class."""

    def __init__(self, source_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            source_class_name: Name of the source class to exclude
        """
        self.source_class_name = source_class_name
        self.other_classes: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit a class definition."""
        if node.name.value != self.source_class_name:
            self.other_classes.append(node.name.value)


class ChangeUnidirectionalToBidirectionalTransformer(cst.CSTTransformer):
    """Transform a unidirectional association into a bidirectional one."""

    def __init__(
        self,
        source_class_name: str,
        field_name: str,
        target_class_name: str,
        back_reference_name: str,
    ) -> None:
        """Initialize the transformer.

        Args:
            source_class_name: Name of the class with the forward reference
            field_name: Name of the field containing the forward reference
            target_class_name: Name of the target class
            back_reference_name: Name for the back reference collection
        """
        self.source_class_name = source_class_name
        self.field_name = field_name
        self.target_class_name = target_class_name
        self.back_reference_name = back_reference_name
        self.private_field_name = f"_{field_name}"

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Modify both classes to establish bidirectional association."""
        if updated_node.name.value == self.source_class_name:
            return self._transform_source_class(updated_node)
        elif updated_node.name.value == self.target_class_name:
            return self._transform_target_class(updated_node)
        return updated_node

    def _transform_source_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the source class to use a setter method."""
        new_body: list[cst.BaseStatement] = []

        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD_NAME:
                    new_body.append(self._transform_source_init(stmt))
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # Add the setter method
        new_body.append(self._create_setter_method())

        return node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _transform_source_init(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform the __init__ method to use setter and private field."""
        new_body: list[cst.BaseStatement] = []

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                modified_stmts = self._transform_init_statement(stmt)
                new_body.extend(modified_stmts)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _transform_init_statement(self, stmt: cst.SimpleStatementLine) -> list[cst.BaseStatement]:
        """Transform statements in __init__ to handle the field assignment."""
        result_statements: list[cst.BaseStatement] = []

        for body_item in stmt.body:
            if isinstance(body_item, cst.Assign):
                # Check if this is assigning to self.customer
                is_field_assignment = False
                for target in body_item.targets:
                    if isinstance(target.target, cst.Attribute):
                        if (
                            isinstance(target.target.value, cst.Name)
                            and target.target.value.value == "self"
                            and target.target.attr.value == self.field_name
                        ):
                            is_field_assignment = True
                            break

                if is_field_assignment:
                    # Replace with: self._customer = None
                    result_statements.append(
                        cst.SimpleStatementLine(
                            body=[
                                cst.Assign(
                                    targets=[
                                        cst.AssignTarget(
                                            target=cst.Attribute(
                                                value=cst.Name("self"),
                                                attr=cst.Name(self.private_field_name),
                                            )
                                        )
                                    ],
                                    value=cst.Name("None"),
                                )
                            ]
                        )
                    )
                    # Then add: self.set_customer(customer)
                    result_statements.append(
                        cst.SimpleStatementLine(
                            body=[
                                cst.Expr(
                                    value=cst.Call(
                                        func=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(f"set_{self.field_name}"),
                                        ),
                                        args=[cst.Arg(value=body_item.value)],
                                    )
                                )
                            ]
                        )
                    )
                else:
                    result_statements.append(stmt)
            else:
                result_statements.append(stmt)

        return result_statements if result_statements else [stmt]

    def _create_setter_method(self) -> cst.FunctionDef:
        """Create the setter method that maintains both sides of the association."""
        return cst.FunctionDef(
            name=cst.Name(f"set_{self.field_name}"),
            params=cst.Parameters(
                params=[create_parameter("self"), create_parameter(self.field_name)]
            ),
            body=cst.IndentedBlock(
                body=[
                    # if self._customer is not None:
                    cst.If(
                        test=cst.Comparison(
                            left=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(self.private_field_name),
                            ),
                            comparisons=[
                                cst.ComparisonTarget(
                                    operator=cst.IsNot(
                                        whitespace_before=cst.SimpleWhitespace(" "),
                                        whitespace_after=cst.SimpleWhitespace(" "),
                                    ),
                                    comparator=cst.Name("None"),
                                )
                            ],
                        ),
                        body=cst.IndentedBlock(
                            body=[
                                # self._customer.remove_order(self)
                                cst.SimpleStatementLine(
                                    body=[
                                        cst.Expr(
                                            value=cst.Call(
                                                func=cst.Attribute(
                                                    value=cst.Attribute(
                                                        value=cst.Name("self"),
                                                        attr=cst.Name(self.private_field_name),
                                                    ),
                                                    attr=cst.Name(
                                                        f"remove_{self.source_class_name.lower()}"
                                                    ),
                                                ),
                                                args=[cst.Arg(value=cst.Name("self"))],
                                            )
                                        )
                                    ]
                                )
                            ]
                        ),
                    ),
                    # self._customer = customer
                    cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(
                                        target=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(self.private_field_name),
                                        )
                                    )
                                ],
                                value=cst.Name(self.field_name),
                            )
                        ]
                    ),
                    # if customer is not None:
                    cst.If(
                        test=cst.Comparison(
                            left=cst.Name(self.field_name),
                            comparisons=[
                                cst.ComparisonTarget(
                                    operator=cst.IsNot(
                                        whitespace_before=cst.SimpleWhitespace(" "),
                                        whitespace_after=cst.SimpleWhitespace(" "),
                                    ),
                                    comparator=cst.Name("None"),
                                )
                            ],
                        ),
                        body=cst.IndentedBlock(
                            body=[
                                # customer.add_order(self)
                                cst.SimpleStatementLine(
                                    body=[
                                        cst.Expr(
                                            value=cst.Call(
                                                func=cst.Attribute(
                                                    value=cst.Name(self.field_name),
                                                    attr=cst.Name(
                                                        f"add_{self.source_class_name.lower()}"
                                                    ),
                                                ),
                                                args=[cst.Arg(value=cst.Name("self"))],
                                            )
                                        )
                                    ]
                                )
                            ]
                        ),
                    ),
                ]
            ),
            leading_lines=[cst.EmptyLine()],
        )

    def _transform_target_class(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the target class to add back reference collection."""
        # Check if class already has an __init__
        has_init = False
        new_body: list[cst.BaseStatement] = []

        for stmt in node.body.body:
            # Skip pass statements
            if isinstance(stmt, cst.SimpleStatementLine):
                if any(isinstance(s, cst.Pass) for s in stmt.body):
                    continue

            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == INIT_METHOD_NAME:
                has_init = True
            new_body.append(cast(cst.BaseStatement, stmt))

        # If no __init__, add one
        if not has_init:
            new_body.insert(0, self._create_target_init())

        # Add helper methods
        new_body.append(self._create_add_method())
        new_body.append(self._create_remove_method())

        return node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_target_init(self) -> cst.FunctionDef:
        """Create __init__ method for target class."""
        return cst.FunctionDef(
            name=cst.Name(INIT_METHOD_NAME),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(
                                        target=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(f"_{self.back_reference_name}"),
                                        )
                                    )
                                ],
                                value=cst.Call(func=cst.Name("set")),
                            )
                        ]
                    )
                ]
            ),
        )

    def _create_add_method(self) -> cst.FunctionDef:
        """Create the add method for the back reference."""
        return cst.FunctionDef(
            name=cst.Name(f"add_{self.source_class_name.lower()}"),
            params=cst.Parameters(
                params=[create_parameter("self"), create_parameter(self.source_class_name.lower())]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(f"_{self.back_reference_name}"),
                                        ),
                                        attr=cst.Name("add"),
                                    ),
                                    args=[cst.Arg(value=cst.Name(self.source_class_name.lower()))],
                                )
                            )
                        ]
                    )
                ]
            ),
            leading_lines=[cst.EmptyLine()],
        )

    def _create_remove_method(self) -> cst.FunctionDef:
        """Create the remove method for the back reference."""
        return cst.FunctionDef(
            name=cst.Name(f"remove_{self.source_class_name.lower()}"),
            params=cst.Parameters(
                params=[create_parameter("self"), create_parameter(self.source_class_name.lower())]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(f"_{self.back_reference_name}"),
                                        ),
                                        attr=cst.Name("discard"),
                                    ),
                                    args=[cst.Arg(value=cst.Name(self.source_class_name.lower()))],
                                )
                            )
                        ]
                    )
                ]
            ),
            leading_lines=[cst.EmptyLine()],
        )


# Register the command
register_command(ChangeUnidirectionalAssociationToBidirectionalCommand)
