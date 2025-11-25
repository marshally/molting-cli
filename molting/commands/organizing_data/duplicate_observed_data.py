"""Duplicate Observed Data refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, parse_target
from molting.core.code_generation_utils import create_parameter

INIT_METHOD_NAME = "__init__"
FIELD_SUFFIX = "_field"


class DuplicateObservedDataCommand(BaseCommand):
    """Command to duplicate domain data in GUI object with observer pattern."""

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
        gui_class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = DuplicateObservedDataTransformer(
            gui_class_name, field_name, domain_class_name
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class DuplicateObservedDataTransformer(cst.CSTTransformer):
    """Transforms GUI class to use domain object with observer pattern."""

    def __init__(self, gui_class_name: str, field_name: str, domain_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            gui_class_name: Name of the GUI class
            field_name: Name of the field that triggered the refactoring
            domain_class_name: Name of the domain class to create
        """
        self.gui_class_name = gui_class_name
        self.field_name = field_name
        self.domain_class_name = domain_class_name
        self.domain_var_name = domain_class_name.lower()
        self.gui_fields_list: list[str] = []
        self.domain_methods: dict[str, cst.FunctionDef] = {}

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the domain class to the module and modify the GUI class."""
        # First pass: analyze the GUI class to extract information
        gui_class = find_class_in_module(updated_node, self.gui_class_name)
        if gui_class and isinstance(gui_class, cst.ClassDef):
            self._analyze_gui_class(gui_class)

        # Create the domain class
        domain_class = self._create_domain_class()
        modified_statements: list[cst.BaseStatement] = [
            domain_class,
            cast(cst.BaseStatement, cst.EmptyLine()),
        ]

        # Modify the GUI class
        for stmt in updated_node.body:
            if stmt is gui_class and isinstance(stmt, cst.ClassDef):
                modified_statements.append(self._modify_gui_class(stmt))
            else:
                modified_statements.append(stmt)

        return updated_node.with_changes(body=tuple(modified_statements))

    def _is_gui_field_attribute(self, attr: cst.Attribute) -> bool:
        """Check if an attribute is a GUI field (self.<name>_field).

        Args:
            attr: The attribute to check

        Returns:
            True if it's a GUI field attribute
        """
        return (
            isinstance(attr.value, cst.Name)
            and attr.value.value == "self"
            and attr.attr.value.endswith(FIELD_SUFFIX)
        )

    def _get_domain_field_name(self, gui_field: str) -> str:
        """Convert GUI field name to domain field name.

        Args:
            gui_field: GUI field name (e.g., 'start_field')

        Returns:
            Domain field name (e.g., 'start')
        """
        return gui_field.replace(FIELD_SUFFIX, "")

    def _analyze_gui_class(self, class_def: cst.ClassDef) -> None:
        """Analyze the GUI class to extract field names and methods.

        Args:
            class_def: The GUI class definition
        """
        gui_fields_list = []
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD_NAME:
                    # Extract field names from __init__ in order
                    for init_stmt in stmt.body.body:
                        if isinstance(init_stmt, cst.SimpleStatementLine):
                            for body_item in init_stmt.body:
                                if isinstance(body_item, cst.Assign):
                                    for target in body_item.targets:
                                        if isinstance(target.target, cst.Attribute):
                                            if self._is_gui_field_attribute(target.target):
                                                field_name = target.target.attr.value
                                                if field_name not in gui_fields_list:
                                                    gui_fields_list.append(field_name)
                elif stmt.name.value == "calculate_length":
                    # Store calculate_length method for domain class
                    self.domain_methods["calculate_length"] = stmt
        # Store as list to preserve order
        self.gui_fields_list = gui_fields_list

    def _create_domain_class(self) -> cst.ClassDef:
        """Create the domain class with business logic.

        Returns:
            New domain class definition
        """
        # Create domain fields from GUI fields in order
        domain_fields = []
        for gui_field in self.gui_fields_list:
            domain_field = self._get_domain_field_name(gui_field)
            domain_fields.append(domain_field)

        # Create __init__ method
        init_body = []
        for field in domain_fields:
            init_body.append(
                cst.SimpleStatementLine(
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

        # Create calculate_length method for domain
        domain_body: list[cst.BaseStatement] = [init_method]
        if "calculate_length" in self.domain_methods:
            domain_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
            domain_calc = self._create_domain_calculate_length()
            domain_body.append(domain_calc)

        return cst.ClassDef(
            name=cst.Name(self.domain_class_name),
            bases=[],
            body=cst.IndentedBlock(body=domain_body),
        )

    def _create_domain_calculate_length(self) -> cst.FunctionDef:
        """Create the calculate_length method for domain class.

        Returns:
            Domain calculate_length method
        """
        return cst.FunctionDef(
            name=cst.Name("calculate_length"),
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
                ]
            ),
        )

    def _modify_gui_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the GUI class to use the domain object.

        Args:
            class_def: The GUI class definition

        Returns:
            Modified GUI class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == INIT_METHOD_NAME:
                    new_body.append(self._modify_gui_init(stmt))
                elif stmt.name.value == "start_field_focus_lost":
                    new_body.append(self._modify_focus_lost_method(stmt))
                elif stmt.name.value == "calculate_length":
                    new_body.append(self._modify_gui_calculate_length(stmt))
                else:
                    new_body.append(stmt)
            else:
                new_body.append(cast(cst.BaseStatement, stmt))

        # Add update method with blank line before it
        new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
        new_body.append(self._create_update_method())

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_gui_init(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify GUI __init__ to create domain object and call update.

        Args:
            init_method: The original __init__ method

        Returns:
            Modified __init__ method
        """
        new_body: list[cst.BaseStatement] = []

        # Add self.interval = Interval()
        new_body.append(
            cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(self.domain_var_name),
                                )
                            )
                        ],
                        value=cst.Call(func=cst.Name(self.domain_class_name), args=[]),
                    )
                ]
            )
        )

        # Keep original field assignments
        for stmt in init_method.body.body:
            new_body.append(stmt)

        # Add self.update() call
        new_body.append(
            cst.SimpleStatementLine(
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
        )

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_focus_lost_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify start_field_focus_lost to update domain object.

        Args:
            method: The original focus lost method

        Returns:
            Modified method
        """
        # Add: self.interval.start = int(self.start_field)
        new_body: list[cst.BaseStatement] = [
            cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                target=cst.Attribute(
                                    value=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(self.domain_var_name),
                                    ),
                                    attr=cst.Name("start"),
                                )
                            )
                        ],
                        value=cst.Call(
                            func=cst.Name("int"),
                            args=[
                                cst.Arg(
                                    value=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name("start_field"),
                                    )
                                )
                            ],
                        ),
                    )
                ]
            )
        ]

        # Keep original body
        for stmt in method.body.body:
            new_body.append(stmt)

        return method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_gui_calculate_length(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify calculate_length to delegate to domain and update GUI.

        Args:
            method: The original calculate_length method

        Returns:
            Modified method
        """
        # Replace body with:
        # self.interval.calculate_length()
        # self.update()
        new_body = [
            cst.SimpleStatementLine(
                body=[
                    cst.Expr(
                        value=cst.Call(
                            func=cst.Attribute(
                                value=cst.Attribute(
                                    value=cst.Name("self"),
                                    attr=cst.Name(self.domain_var_name),
                                ),
                                attr=cst.Name("calculate_length"),
                            ),
                            args=[],
                        )
                    )
                ]
            ),
            cst.SimpleStatementLine(
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
            ),
        ]

        return method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_update_method(self) -> cst.FunctionDef:
        """Create the update method to sync GUI fields with domain data.

        Returns:
            The update method
        """
        # Create statements for each field in order
        statements = []
        for gui_field in self.gui_fields_list:
            domain_field = self._get_domain_field_name(gui_field)
            statements.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(gui_field),
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
                                                attr=cst.Name(self.domain_var_name),
                                            ),
                                            attr=cst.Name(domain_field),
                                        )
                                    )
                                ],
                            ),
                        )
                    ]
                )
            )

        return cst.FunctionDef(
            name=cst.Name("update"),
            params=cst.Parameters(params=[create_parameter("self")]),
            body=cst.IndentedBlock(body=statements),
        )


# Register the command
register_command(DuplicateObservedDataCommand)
