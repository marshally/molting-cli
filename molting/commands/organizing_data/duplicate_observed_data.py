"""Duplicate Observed Data refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    extract_init_field_assignments,
    find_class_in_module,
    find_method_in_class,
    parse_target,
)
from molting.core.code_generation_utils import create_parameter

INIT_METHOD_NAME = "__init__"


class DuplicateObservedDataCommand(BaseCommand):
    """Duplicate Observed Data refactoring: Separate GUI data from domain logic.

    This refactoring addresses the problem of mixing GUI widget state with domain
    logic. When a GUI class directly holds data (such as text field values) that
    represents domain concepts, changes to the GUI must be synchronized with
    domain calculations, creating tight coupling and making the domain logic
    hard to test in isolation.

    The refactoring creates a separate domain class to hold the actual data and
    computations, while the GUI class maintains its own representation. An update
    mechanism synchronizes them: domain data flows back to the GUI for display,
    and GUI changes flow to the domain for computation.

    **When to use:**
    - GUI classes hold data that should logically belong to domain objects
    - Domain calculations depend on GUI widget state
    - You want to test business logic independently of UI frameworks
    - GUI and domain share the same data with tight coupling
    - You need to display domain data in a GUI without mixing concerns

    **Example:**
    Before:
        class IntervalUI:
            def __init__(self):
                self.start_field = TextField()
                self.end_field = TextField()
                self.length_field = TextField()

            def calculate_length(self):
                # Domain logic embedded in GUI class
                self.length_field.set_value(
                    int(self.end_field.value) - int(self.start_field.value)
                )

    After:
        class Interval:  # Domain class
            def __init__(self):
                self.start = 0
                self.end = 0
                self.length = 0

            def calculate_length(self):
                self.length = self.end - self.start

        class IntervalUI:
            def __init__(self):
                self.interval = Interval()  # Domain object
                self.start_field = TextField()
                self.end_field = TextField()
                self.length_field = TextField()
                self.update()

            def start_field_focus_lost(self):
                # GUI change updates domain
                self.interval.start = int(self.start_field.value)
                self.update()

            def update(self):
                # Domain data synchronized to GUI display
                self.start_field.set_value(str(self.interval.start))
                self.length_field.set_value(str(self.interval.length))
    """

    name = "duplicate-observed-data"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError("Missing required parameter for duplicate-observed-data: 'target'")
        if "domain" not in self.params:
            raise ValueError("Missing required parameter for duplicate-observed-data: 'domain'")

    def execute(self) -> None:
        """Apply duplicate-observed-data refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        domain_class_name = self.params["domain"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = DuplicateObservedDataTransformer(class_name, field_name, domain_class_name)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class DuplicateObservedDataTransformer(cst.CSTTransformer):
    """Transforms GUI class to extract domain logic into separate domain class."""

    def __init__(self, gui_class_name: str, target_field: str, domain_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            gui_class_name: Name of the GUI class
            target_field: Name of the field that triggered the refactoring
            domain_class_name: Name of the domain class to create
        """
        self.gui_class_name = gui_class_name
        self.target_field = target_field
        self.domain_class_name = domain_class_name
        self.gui_fields: list[str] = []
        self.domain_field_name = self._generate_domain_field_name()

    def _generate_domain_field_name(self) -> str:
        """Generate field name for the domain object instance.

        Returns:
            Field name in snake_case based on domain class name
        """
        # Convert CamelCase to snake_case
        name = self.domain_class_name
        snake_case = "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")
        return snake_case

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add domain class and modify GUI class."""
        # Find the GUI class to analyze
        gui_class = find_class_in_module(updated_node, self.gui_class_name)
        if gui_class is None:
            return updated_node

        # Extract field information from __init__ (preserving order)
        init_method = find_method_in_class(gui_class, INIT_METHOD_NAME)
        if init_method:
            field_assignments = extract_init_field_assignments(init_method)
            self.gui_fields = list(field_assignments.keys())

        # Create domain class
        domain_class = self._create_domain_class()

        # Build new module with domain class first, then modified GUI class
        new_statements: list[cst.BaseStatement] = [
            domain_class,
            cast(cst.BaseStatement, cst.EmptyLine()),
            cast(cst.BaseStatement, cst.EmptyLine()),
        ]

        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.gui_class_name:
                modified_gui_class = self._modify_gui_class(stmt)
                new_statements.append(modified_gui_class)
            else:
                new_statements.append(stmt)

        return updated_node.with_changes(body=tuple(new_statements))

    def _create_domain_class(self) -> cst.ClassDef:
        """Create the domain class with fields and calculate method.

        Returns:
            Domain class definition
        """
        # Create __init__ method for domain class
        init_body = []
        for field in self.gui_fields:
            if field.endswith("_field"):
                # Convert field_name_field to field_name
                domain_field = field[: -len("_field")]
                init_body.append(
                    cst.SimpleStatementLine(
                        body=[
                            cst.Assign(
                                targets=[
                                    cst.AssignTarget(
                                        target=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name(domain_field),
                                        )
                                    )
                                ],
                                value=cst.Integer("0"),
                            )
                        ]
                    )
                )

        init_method = cst.FunctionDef(
            name=cst.Name(INIT_METHOD_NAME),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(body=init_body),
        )

        # Create calculate_length method
        calculate_method = self._create_calculate_method()

        return cst.ClassDef(
            name=cst.Name(self.domain_class_name),
            bases=[],
            body=cst.IndentedBlock(
                body=[
                    init_method,
                    cast(cst.BaseStatement, cst.EmptyLine()),
                    calculate_method,
                ]
            ),
        )

    def _create_calculate_method(self) -> cst.FunctionDef:
        """Create the calculate_length method for the domain class.

        Returns:
            Method definition
        """
        # Create: self.length = self.end - self.start
        calculate_body = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name("length"),
                            )
                        )
                    ],
                    value=cst.BinaryOperation(
                        left=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name("end"),
                        ),
                        operator=cst.Subtract(),
                        right=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name("start"),
                        ),
                    ),
                )
            ]
        )

        return cst.FunctionDef(
            name=cst.Name("calculate_length"),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(body=[calculate_body]),
        )

    def _modify_gui_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify GUI class to use domain object.

        Args:
            class_def: The GUI class definition

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD_NAME:
                    modified_init = self._modify_init_method(stmt)
                    new_body.append(modified_init)
                elif stmt.name.value == "start_field_focus_lost":
                    modified_method = self._modify_focus_lost_method(stmt)
                    new_body.append(modified_method)
                elif stmt.name.value == "calculate_length":
                    modified_method = self._modify_calculate_method_delegation(stmt)
                    new_body.append(modified_method)
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # Add update method at the end
        new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
        new_body.append(self._create_update_method())

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_init_method(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify __init__ to create domain object instance and call update.

        Args:
            init_method: The __init__ method

        Returns:
            Modified __init__ method
        """
        new_body_stmts: list[cst.BaseStatement] = []

        # Add domain object instantiation first
        domain_instantiation = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(self.domain_field_name),
                            )
                        )
                    ],
                    value=cst.Call(func=cst.Name(self.domain_class_name), args=[]),
                )
            ]
        )
        new_body_stmts.append(domain_instantiation)

        # Keep existing field initializations
        for stmt in init_method.body.body:
            new_body_stmts.append(cast(cst.BaseStatement, stmt))

        # Add call to update()
        update_call = cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name("update"),
                        ),
                        args=[],
                    )
                )
            ]
        )
        new_body_stmts.append(update_call)

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body_stmts))

    def _modify_focus_lost_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify focus lost method to update domain object.

        Args:
            method: The focus lost method

        Returns:
            Modified method
        """
        # Create: self.interval.start = int(self.start_field)
        field_name = self.target_field.replace("_field", "")
        update_domain = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[
                        cst.AssignTarget(
                            target=cst.Attribute(
                                value=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(self.domain_field_name),
                                ),
                                attr=cst.Name(field_name),
                            )
                        )
                    ],
                    value=cst.Call(
                        func=cst.Name("int"),
                        args=[
                            cst.Arg(
                                value=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(self.target_field),
                                )
                            )
                        ],
                    ),
                )
            ]
        )

        # Keep original method call
        new_body: list[cst.SimpleStatementLine] = [update_domain]
        for stmt in method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                new_body.append(stmt)

        return method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_calculate_method_delegation(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify calculate_length to delegate to domain object.

        Args:
            method: The calculate_length method

        Returns:
            Modified method that delegates and calls update
        """
        # Create method body that delegates to domain and calls update
        delegate_call = cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(self.domain_field_name),
                            ),
                            attr=cst.Name("calculate_length"),
                        ),
                        args=[],
                    )
                )
            ]
        )

        update_call = cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name("update"),
                        ),
                        args=[],
                    )
                )
            ]
        )

        return method.with_changes(body=cst.IndentedBlock(body=[delegate_call, update_call]))

    def _create_update_method(self) -> cst.FunctionDef:
        """Create update method to sync GUI fields with domain object.

        Returns:
            Update method definition
        """
        update_body: list[cst.BaseStatement] = []

        # Create update statements for each field
        for field in self.gui_fields:
            if field.endswith("_field"):
                domain_field = field[: -len("_field")]
                # Create: self.field_name_field = str(self.interval.field_name)
                update_stmt = cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(field),
                                    )
                                )
                            ],
                            value=cst.Call(
                                func=cst.Name("str"),
                                args=[
                                    cst.Arg(
                                        value=cst.Attribute(
                                            value=cst.Attribute(
                                                value=cst.Name("self"),
                                                attr=cst.Name(self.domain_field_name),
                                            ),
                                            attr=cst.Name(domain_field),
                                        )
                                    )
                                ],
                            ),
                        )
                    ]
                )
                update_body.append(update_stmt)

        return cst.FunctionDef(
            name=cst.Name("update"),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(body=update_body),
        )


# Register the command
register_command(DuplicateObservedDataCommand)
