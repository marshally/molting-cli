"""Change Unidirectional Association to Bidirectional refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, parse_target
from molting.core.code_generation_utils import create_parameter


class ChangeUnidirectionalAssociationToBidirectionalCommand(BaseCommand):
    """Command to change unidirectional association to bidirectional."""

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
        """Apply change-unidirectional-association-to-bidirectional refactoring.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        back_reference_name = self.params["back"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ChangeUnidirectionalAssociationToBidirectionalTransformer(
            class_name, field_name, back_reference_name
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ChangeUnidirectionalAssociationToBidirectionalTransformer(cst.CSTTransformer):
    """Transforms unidirectional association to bidirectional."""

    def __init__(self, class_name: str, field_name: str, back_reference_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the unidirectional association
            field_name: Name of the field (e.g., 'customer')
            back_reference_name: Name of the back reference field (e.g., 'orders')
        """
        self.class_name = class_name
        self.field_name = field_name
        self.back_reference_name = back_reference_name
        self.reference_class_name: str | None = None

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Transform the module to add bidirectional association."""
        # First pass: find the reference class by analyzing the original class
        target_class = find_class_in_module(updated_node, self.class_name)
        self._extract_reference_class_name(target_class)

        if self.reference_class_name is None:
            return updated_node

        # Transform module
        new_statements: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.class_name:
                    new_statements.append(self._modify_forward_class(stmt))
                elif stmt.name.value == self.reference_class_name:
                    new_statements.append(self._modify_reference_class(stmt))
                else:
                    new_statements.append(stmt)
            else:
                new_statements.append(stmt)

        return updated_node.with_changes(body=tuple(new_statements))

    def _extract_reference_class_name(self, class_def: cst.ClassDef | None) -> None:
        """Extract the reference class name from the __init__ method.

        Args:
            class_def: The class definition to analyze
        """
        if class_def is None or not isinstance(class_def.body, cst.IndentedBlock):
            return

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                for body_stmt in stmt.body.body:
                    if isinstance(body_stmt, cst.SimpleStatementLine):
                        for item in body_stmt.body:
                            if isinstance(item, cst.Assign):
                                for target in item.targets:
                                    if isinstance(target.target, cst.Attribute):
                                        if (
                                            isinstance(target.target.value, cst.Name)
                                            and target.target.value.value == "self"
                                            and target.target.attr.value == self.field_name
                                        ):
                                            # Get the class name from the parameter
                                            if isinstance(item.value, cst.Name):
                                                self.reference_class_name = (
                                                    item.value.value.capitalize()
                                                )

    def _modify_forward_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the forward class to use a setter method.

        Args:
            class_def: The class definition

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                new_body.append(self._modify_forward_init(stmt))
            else:
                new_body.append(stmt)

        # Add the setter method
        new_body.append(self._create_setter_method())

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_forward_init(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify __init__ to initialize field as None and use setter.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                modified = False
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Attribute):
                                if (
                                    isinstance(target.target.value, cst.Name)
                                    and target.target.value.value == "self"
                                    and target.target.attr.value == self.field_name
                                ):
                                    # Initialize private field as None
                                    new_body_stmts.append(
                                        cst.SimpleStatementLine(
                                            body=[
                                                cst.Assign(
                                                    targets=[
                                                        cst.AssignTarget(
                                                            target=cst.Attribute(
                                                                value=cst.Name("self"),
                                                                attr=cst.Name(
                                                                    f"_{self.field_name}"
                                                                ),
                                                            )
                                                        )
                                                    ],
                                                    value=cst.Name("None"),
                                                )
                                            ]
                                        )
                                    )
                                    # Call setter
                                    new_body_stmts.append(
                                        cst.SimpleStatementLine(
                                            body=[
                                                cst.Expr(
                                                    cst.Call(
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
                                    modified = True
                                    break
                if not modified:
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(cast(cst.BaseStatement, stmt))

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body_stmts))

    def _create_setter_method(self) -> cst.FunctionDef:
        """Create the setter method for the field.

        Returns:
            The setter method
        """
        return cst.FunctionDef(
            name=cst.Name(f"set_{self.field_name}"),
            params=cst.Parameters(
                params=[
                    create_parameter("self"),
                    create_parameter(self.field_name),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    # if self._field is not None:
                    cst.If(
                        test=cst.Comparison(
                            left=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(f"_{self.field_name}"),
                            ),
                            comparisons=[
                                cst.ComparisonTarget(
                                    operator=cst.IsNot(),
                                    comparator=cst.Name("None"),
                                )
                            ],
                        ),
                        body=cst.IndentedBlock(
                            body=[
                                # self._field.remove_*()
                                cst.SimpleStatementLine(
                                    body=[
                                        cst.Expr(
                                            cst.Call(
                                                func=cst.Attribute(
                                                    value=cst.Attribute(
                                                        value=cst.Name("self"),
                                                        attr=cst.Name(f"_{self.field_name}"),
                                                    ),
                                                    attr=cst.Name(
                                                        f"remove_{self.class_name.lower()}"
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
                    # self._field = field
                    cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(
                                        target=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(f"_{self.field_name}"),
                                        )
                                    )
                                ],
                                value=cst.Name(self.field_name),
                            )
                        ]
                    ),
                    # if field is not None:
                    cst.If(
                        test=cst.Comparison(
                            left=cst.Name(self.field_name),
                            comparisons=[
                                cst.ComparisonTarget(
                                    operator=cst.IsNot(),
                                    comparator=cst.Name("None"),
                                )
                            ],
                        ),
                        body=cst.IndentedBlock(
                            body=[
                                # field.add_*()
                                cst.SimpleStatementLine(
                                    body=[
                                        cst.Expr(
                                            cst.Call(
                                                func=cst.Attribute(
                                                    value=cst.Name(self.field_name),
                                                    attr=cst.Name(f"add_{self.class_name.lower()}"),
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
        )

    def _modify_reference_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the reference class to add the back pointer collection.

        Args:
            class_def: The reference class definition

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []
        has_init = False

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                has_init = True
                new_body.append(self._modify_reference_init(stmt))
            elif isinstance(stmt, cst.SimpleStatementLine):
                # Skip pass statements if we're adding methods
                has_pass = False
                for item in stmt.body:
                    if isinstance(item, cst.Pass):
                        has_pass = True
                        break
                if not has_pass:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        # If no __init__, create one
        if not has_init:
            new_body.insert(0, self._create_reference_init())

        # Add accessor methods
        new_body.append(self._create_add_method(self.class_name.lower(), self.back_reference_name))
        new_body.append(
            self._create_remove_method(self.class_name.lower(), self.back_reference_name)
        )

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_reference_init(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify __init__ to add back pointer collection initialization.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body_stmts: list[cst.BaseStatement] = list(init_method.body.body)

        # Add initialization of back reference
        new_body_stmts.insert(
            0,
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
                        value=cst.Call(func=cst.Name("set"), args=[]),
                    )
                ]
            ),
        )

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body_stmts))

    def _create_reference_init(self) -> cst.FunctionDef:
        """Create __init__ for reference class if it doesn't exist.

        Returns:
            The __init__ method
        """
        return cst.FunctionDef(
            name=cst.Name("__init__"),
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
                                value=cst.Call(func=cst.Name("set"), args=[]),
                            )
                        ]
                    )
                ]
            ),
        )

    def _create_add_method(self, singular_name: str, collection_name: str) -> cst.FunctionDef:
        """Create the add method for the back reference.

        Args:
            singular_name: Singular form of the class name (e.g., 'order')
            collection_name: Name of the collection (e.g., 'orders')

        Returns:
            The add method
        """
        return cst.FunctionDef(
            name=cst.Name(f"add_{singular_name}"),
            params=cst.Parameters(
                params=[
                    create_parameter("self"),
                    create_parameter(singular_name),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Expr(
                                cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(f"_{collection_name}"),
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
        )

    def _create_remove_method(self, singular_name: str, collection_name: str) -> cst.FunctionDef:
        """Create the remove method for the back reference.

        Args:
            singular_name: Singular form of the class name (e.g., 'order')
            collection_name: Name of the collection (e.g., 'orders')

        Returns:
            The remove method
        """
        return cst.FunctionDef(
            name=cst.Name(f"remove_{singular_name}"),
            params=cst.Parameters(
                params=[
                    create_parameter("self"),
                    create_parameter(singular_name),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Expr(
                                cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(f"_{collection_name}"),
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
        )


# Register the command
register_command(ChangeUnidirectionalAssociationToBidirectionalCommand)
