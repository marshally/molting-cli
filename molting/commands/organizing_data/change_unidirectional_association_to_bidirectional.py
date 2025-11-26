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
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for "
                "change-unidirectional-association-to-bidirectional: 'target'"
            )
        if "back" not in self.params:
            raise ValueError(
                "Missing required parameter for "
                "change-unidirectional-association-to-bidirectional: 'back'"
            )

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

        # Find the referenced class by analyzing the code
        finder = ClassFinder()
        module.visit(finder)

        # Determine which class is which
        if class_name in finder.classes:
            forward_class = class_name
            # The other class must be the back reference class
            back_class = None
            for cls in finder.classes:
                if cls != forward_class:
                    back_class = cls
                    break
        else:
            raise ValueError(f"Class {class_name} not found")

        if back_class is None:
            raise ValueError("Could not find the back reference class")

        transformer = ChangeUnidirectionalAssociationToBidirectionalTransformer(
            forward_class, field_name, back_class, back_name
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ClassFinder(cst.CSTVisitor):
    """Visitor to find all class names in the module."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        self.classes: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Record class names."""
        self.classes.append(node.name.value)


class ChangeUnidirectionalAssociationToBidirectionalTransformer(cst.CSTTransformer):
    """Transforms a unidirectional association to bidirectional."""

    def __init__(
        self, forward_class: str, field_name: str, back_class: str, back_name: str
    ) -> None:
        """Initialize the transformer.

        Args:
            forward_class: Name of the class with the forward reference
            field_name: Name of the field in the forward class
            back_class: Name of the class to add the back reference to
            back_name: Name of the back reference field
        """
        self.forward_class = forward_class
        self.field_name = field_name
        self.private_field_name = f"_{field_name}"
        self.back_class = back_class
        self.back_name = back_name
        self.private_back_name = f"_{back_name}"

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Modify classes to create bidirectional association."""
        if updated_node.name.value == self.forward_class:
            return self._transform_forward_class(updated_node)
        elif updated_node.name.value == self.back_class:
            return self._transform_back_class(updated_node)
        return updated_node

    def _transform_forward_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Transform the forward class to use setter method."""
        new_body: list[cst.BaseStatement] = []

        for stmt in class_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD_NAME:
                    new_body.append(self._transform_forward_init(stmt))
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # Add setter method
        new_body.append(self._create_setter_method())

        return class_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _transform_forward_init(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Transform __init__ to initialize private field and call setter.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body: list[cst.BaseStatement] = []
        param_name = None

        # Find the parameter name for the field
        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Attribute):
                                if (
                                    isinstance(target.target.value, cst.Name)
                                    and target.target.value.value == "self"
                                    and target.target.attr.value == self.field_name
                                ):
                                    if isinstance(body_item.value, cst.Name):
                                        param_name = body_item.value.value

        # Create new body:
        # 1. self._customer = None
        # 2. self.set_customer(customer)
        new_body.append(
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

        if param_name:
            new_body.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Expr(
                            value=cst.Call(
                                func=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(f"set_{self.field_name}"),
                                ),
                                args=[cst.Arg(value=cst.Name(param_name))],
                            )
                        )
                    ]
                )
            )

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_setter_method(self) -> cst.FunctionDef:
        """Create the setter method for managing bidirectional relationship.

        Returns:
            Setter method
        """
        # Build method body
        body_statements: list[cst.BaseStatement] = []

        # if self._customer is not None:
        #     self._customer.remove_order(self)
        body_statements.append(
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        value=cst.Name("self"), attr=cst.Name(self.private_field_name)
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
                        cst.SimpleStatementLine(
                            body=[
                                cst.Expr(
                                    value=cst.Call(
                                        func=cst.Attribute(
                                            value=cst.Attribute(
                                                value=cst.Name("self"),
                                                attr=cst.Name(self.private_field_name),
                                            ),
                                            attr=cst.Name(f"remove_{self.back_name.rstrip('s')}"),
                                        ),
                                        args=[cst.Arg(value=cst.Name("self"))],
                                    )
                                )
                            ]
                        )
                    ]
                ),
            )
        )

        # self._customer = customer
        body_statements.append(
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
            )
        )

        # if customer is not None:
        #     customer.add_order(self)
        body_statements.append(
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
                        cst.SimpleStatementLine(
                            body=[
                                cst.Expr(
                                    value=cst.Call(
                                        func=cst.Attribute(
                                            value=cst.Name(self.field_name),
                                            attr=cst.Name(f"add_{self.back_name.rstrip('s')}"),
                                        ),
                                        args=[cst.Arg(value=cst.Name("self"))],
                                    )
                                )
                            ]
                        )
                    ]
                ),
            )
        )

        return cst.FunctionDef(
            name=cst.Name(f"set_{self.field_name}"),
            params=cst.Parameters(
                params=[create_parameter("self"), create_parameter(self.field_name)]
            ),
            body=cst.IndentedBlock(body=body_statements),
            leading_lines=[cst.EmptyLine()],
        )

    def _transform_back_class(self, class_node: cst.ClassDef) -> cst.ClassDef:
        """Transform the back class to add collection and helper methods."""
        new_body: list[cst.BaseStatement] = []
        has_init = False

        for stmt in class_node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == INIT_METHOD_NAME:
                has_init = True
            # Skip pass statements if we're going to add an __init__
            if isinstance(stmt, cst.SimpleStatementLine):
                if any(isinstance(s, cst.Pass) for s in stmt.body):
                    continue
            new_body.append(cast(cst.BaseStatement, stmt))

        # If no __init__, add one
        if not has_init:
            new_body.insert(0, self._create_back_init())

        # Add add_order method
        new_body.append(self._create_add_method())

        # Add remove_order method
        new_body.append(self._create_remove_method())

        return class_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_back_init(self) -> cst.FunctionDef:
        """Create __init__ method for the back class.

        Returns:
            __init__ method
        """
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
                                            attr=cst.Name(self.private_back_name),
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
        """Create add method for the back class.

        Returns:
            add method
        """
        singular_name = self.back_name.rstrip("s")
        return cst.FunctionDef(
            name=cst.Name(f"add_{singular_name}"),
            params=cst.Parameters(
                params=[create_parameter("self"), create_parameter(singular_name)]
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
                                            attr=cst.Name(self.private_back_name),
                                        ),
                                        attr=cst.Name("add"),
                                    ),
                                    args=[cst.Arg(value=cst.Name(singular_name))],
                                )
                            )
                        ]
                    )
                ]
            ),
            leading_lines=[cst.EmptyLine()],
        )

    def _create_remove_method(self) -> cst.FunctionDef:
        """Create remove method for the back class.

        Returns:
            remove method
        """
        singular_name = self.back_name.rstrip("s")
        return cst.FunctionDef(
            name=cst.Name(f"remove_{singular_name}"),
            params=cst.Parameters(
                params=[create_parameter("self"), create_parameter(singular_name)]
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
                                            attr=cst.Name(self.private_back_name),
                                        ),
                                        attr=cst.Name("discard"),
                                    ),
                                    args=[cst.Arg(value=cst.Name(singular_name))],
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
