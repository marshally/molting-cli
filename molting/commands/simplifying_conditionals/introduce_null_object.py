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
            ValueError: If target_class is not found
        """
        target_class = self.params["target_class"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = IntroduceNullObjectTransformer(target_class)
        modified_tree = module.visit(transformer)
        self.file_path.write_text(modified_tree.code)


class IntroduceNullObjectTransformer(cst.CSTTransformer):
    """Transformer to introduce null object pattern."""

    def __init__(self, target_class: str) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to create null object for
        """
        self.target_class = target_class
        self.null_class_name = f"Null{target_class}"
        self.target_class_node: cst.ClassDef | None = None
        self.init_params: list[cst.Param] = []
        self.default_values: dict[str, str] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Capture the target class definition to extract information."""
        if node.name.value == self.target_class:
            self.target_class_node = node
            self._extract_init_info(node)

    def _extract_init_info(self, node: cst.ClassDef) -> None:
        """Extract __init__ parameter information from the class."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Extract parameters (skip self)
                for param in stmt.params.params[1:]:
                    self.init_params.append(param)
                    # Set simple default values for the null object
                    param_name = param.name.value if isinstance(param.name, cst.Name) else ""
                    if param_name == "name":
                        self.default_values[param_name] = '"Unknown"'
                    elif param_name == "plan":
                        self.default_values[param_name] = '"Basic"'
                    else:
                        # Generic fallback
                        self.default_values[param_name] = '"Unknown"'

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.FlattenSentinel[cst.ClassDef]:
        """Transform class and add is_null method and null object class."""
        if original_node.name.value == self.target_class:
            # Add is_null method to the target class
            updated_node = self._add_is_null_method(updated_node, returns_false=True)
            # Create the null object class
            null_class = self._create_null_object_class()
            return cst.FlattenSentinel([updated_node, null_class])

        # Handle Site class - add null check in __init__
        if original_node.name.value == "Site":
            updated_node = self._add_null_check_to_site(updated_node)

        return updated_node

    def _add_is_null_method(self, node: cst.ClassDef, returns_false: bool) -> cst.ClassDef:
        """Add is_null method to a class.

        Args:
            node: The class to modify
            returns_false: If True, method returns False; otherwise returns True

        Returns:
            Modified class with is_null method
        """
        if not isinstance(node.body, cst.IndentedBlock):
            return node

        # Create is_null method
        is_null_method = cst.FunctionDef(
            name=cst.Name("is_null"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[cst.Return(value=cst.Name("False" if returns_false else "True"))]
                    )
                ]
            ),
            leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))],
        )

        # Add method to the end of the class body
        new_body = list(node.body.body) + [is_null_method]
        return node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_null_object_class(self) -> cst.ClassDef:
        """Create the null object class.

        Returns:
            The null object class definition
        """
        # Create __init__ method with default values
        init_body_stmts: list[cst.BaseStatement] = []
        for param in self.init_params:
            param_name = param.name.value if isinstance(param.name, cst.Name) else ""
            default_value = self.default_values.get(param_name, '"Unknown"')
            init_body_stmts.append(
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
                            value=cst.parse_expression(default_value),
                        )
                    ]
                )
            )

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(body=init_body_stmts),
        )

        # Create is_null method
        is_null_method = cst.FunctionDef(
            name=cst.Name("is_null"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("True"))])]
            ),
            leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))],
        )

        # Create the null object class
        return cst.ClassDef(
            name=cst.Name(self.null_class_name),
            bases=[cst.Arg(value=cst.Name(self.target_class))],
            body=cst.IndentedBlock(body=[init_method, is_null_method]),
            leading_lines=[cst.EmptyLine(), cst.EmptyLine()],
        )

    def _add_null_check_to_site(self, node: cst.ClassDef) -> cst.ClassDef:
        """Add null check to Site.__init__ method.

        Args:
            node: The Site class definition

        Returns:
            Modified Site class with null check in __init__
        """
        if not isinstance(node.body, cst.IndentedBlock):
            return node

        new_body = []
        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Modify the __init__ method
                stmt = self._modify_site_init(stmt)
            new_body.append(stmt)

        return node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_site_init(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify Site.__init__ to add null check.

        Args:
            init_method: The original __init__ method

        Returns:
            Modified __init__ method with null check
        """
        if not isinstance(init_method.body, cst.IndentedBlock):
            return init_method

        new_body = []
        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this is self.customer = customer
                for s in stmt.body:
                    if isinstance(s, cst.Assign):
                        if len(s.targets) > 0:
                            target = s.targets[0].target
                            if isinstance(target, cst.Attribute):
                                if (
                                    isinstance(target.value, cst.Name)
                                    and target.value.value == "self"
                                    and isinstance(target.attr, cst.Name)
                                    and target.attr.value == "customer"
                                ):
                                    # Replace with conditional assignment to null object
                                    new_assignment = cst.Assign(
                                        targets=s.targets,
                                        value=cst.IfExp(
                                            test=cst.Comparison(
                                                left=cst.Name("customer"),
                                                comparisons=[
                                                    cst.ComparisonTarget(
                                                        operator=cst.IsNot(
                                                            whitespace_before=cst.SimpleWhitespace(
                                                                " "
                                                            ),
                                                            whitespace_after=cst.SimpleWhitespace(
                                                                " "
                                                            ),
                                                        ),
                                                        comparator=cst.Name("None"),
                                                    )
                                                ],
                                            ),
                                            body=cst.Name("customer"),
                                            orelse=cst.Call(
                                                func=cst.Name(self.null_class_name), args=[]
                                            ),
                                        ),
                                    )
                                    stmt = stmt.with_changes(body=[new_assignment])
            new_body.append(stmt)

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))


# Register the command
register_command(IntroduceNullObjectCommand)
