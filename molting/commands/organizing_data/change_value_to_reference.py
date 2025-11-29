"""Change Value to Reference refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.code_generation_utils import create_parameter

INIT_METHOD_NAME = "__init__"


class ChangeValueToReferenceCommand(BaseCommand):
    """Transform a value object into a reference object with identity-based sharing.

    The Change Value to Reference refactoring converts a value object (an object
    whose identity is determined by its data) into a reference object (an object
    whose identity is based on shared instance equality). This is done by introducing
    a registry to ensure only one instance exists for each unique identity, and
    replacing all instantiations with calls to a factory method that returns the
    shared instance.

    **When to use:**
    - You have many equal instances of a class that should actually be the same
      shared object (e.g., multiple Customer instances with the same ID should
      reference the same object across your application)
    - Creating a new instance every time is wasteful when the same logical entity
      already exists in memory
    - You need to ensure referential equality for objects with the same identity
    - The object is essentially immutable or has a stable identity

    **Example:**
    Before:
        customer1 = Customer("Alice")
        customer2 = Customer("Alice")
        assert customer1 is not customer2  # Two separate instances
        assert customer1 == customer2      # But equal by value

    After:
        customer1 = Customer.get_named("Alice")
        customer2 = Customer.get_named("Alice")
        assert customer1 is customer2      # Same shared instance
        assert customer1 == customer2      # Also equal by value
    """

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
        target = self.params["target"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ChangeValueToReferenceTransformer(target)
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ChangeValueToReferenceTransformer(cst.CSTTransformer):
    """Transforms a value object into a reference object with registry."""

    def __init__(self, class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to convert to reference
        """
        self.class_name = class_name
        self.init_param_name: str | None = None

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Modify the target class to add registry and factory method."""
        new_statements: list[cst.BaseStatement] = []

        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.class_name:
                # Extract init parameter name before modifying the class
                self._extract_init_param_name(stmt)
                # Modify the class to add registry and factory method
                modified_class = self._modify_class(stmt)
                new_statements.append(modified_class)
            else:
                new_statements.append(stmt)

        # Update all instantiations of the class to use the factory method
        final_module = updated_node.with_changes(body=tuple(new_statements))
        instantiation_transformer = ReplaceInstantiationTransformer(self.class_name)
        return final_module.visit(instantiation_transformer)

    def _extract_init_param_name(self, class_def: cst.ClassDef) -> None:
        """Extract the parameter name from __init__ method.

        Args:
            class_def: The class definition to analyze
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == INIT_METHOD_NAME:
                # Get the first parameter after 'self'
                if len(stmt.params.params) > 1:
                    self.init_param_name = stmt.params.params[1].name.value
                break

    def _modify_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Add registry and factory method to the class.

        Args:
            class_def: The class definition to modify

        Returns:
            Modified class definition with registry and factory method
        """
        # Create the _instances class variable
        instances_var = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("_instances"))],
                    value=cst.Dict(elements=[]),
                )
            ]
        )

        # Create empty line for spacing
        empty_line = cst.EmptyLine()

        # Create the get_named class method
        param_name = self.init_param_name or "name"
        get_named_method = self._create_get_named_method(param_name)

        # Build new body with registry and factory method
        new_body: list[cst.BaseStatement] = [
            instances_var,
            cast(cst.BaseStatement, empty_line),
        ]

        # Add existing class body
        for stmt in class_def.body.body:
            new_body.append(cast(cst.BaseStatement, stmt))

        # Add empty line before get_named method
        new_body.append(cast(cst.BaseStatement, empty_line))
        new_body.append(get_named_method)

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_get_named_method(self, param_name: str) -> cst.FunctionDef:
        """Create the get_named class method.

        Args:
            param_name: The parameter name from __init__

        Returns:
            The get_named class method
        """
        # Create the if statement: if name not in cls._instances:
        if_statement = cst.If(
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
                                                    slice=cst.Index(value=cst.Name(param_name))
                                                )
                                            ],
                                        )
                                    )
                                ],
                                value=cst.Call(
                                    func=cst.Name(self.class_name),
                                    args=[cst.Arg(value=cst.Name(param_name))],
                                ),
                            )
                        ]
                    )
                ]
            ),
        )

        # Create the return statement: return cls._instances[name]
        return_statement = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Subscript(
                        value=cst.Attribute(
                            value=cst.Name("cls"),
                            attr=cst.Name("_instances"),
                        ),
                        slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name(param_name)))],
                    )
                )
            ]
        )

        # Create the complete method
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
                    if_statement,
                    return_statement,
                ]
            ),
            decorators=[
                cst.Decorator(
                    decorator=cst.Name("classmethod"),
                )
            ],
        )


class ReplaceInstantiationTransformer(cst.CSTTransformer):
    """Replaces direct class instantiation with factory method calls."""

    def __init__(self, class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class whose instantiation to replace
        """
        self.class_name = class_name
        self.inside_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Track when we're inside the target class.

        Args:
            node: The class definition node
        """
        if node.name.value == self.class_name:
            self.inside_target_class = True

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Track when we're leaving the target class.

        Args:
            original_node: The original class node
            updated_node: The updated class node

        Returns:
            The unchanged class node
        """
        if original_node.name.value == self.class_name:
            self.inside_target_class = False
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Replace Class(arg) with Class.get_named(arg).

        Args:
            original_node: The original call node
            updated_node: The updated call node

        Returns:
            Transformed call node
        """
        # Don't replace instantiations inside the target class itself
        if self.inside_target_class:
            return updated_node

        # Check if this is a direct instantiation of the target class
        if isinstance(updated_node.func, cst.Name) and updated_node.func.value == self.class_name:
            # Replace with Class.get_named(args)
            return updated_node.with_changes(
                func=cst.Attribute(
                    value=cst.Name(self.class_name),
                    attr=cst.Name("get_named"),
                )
            )

        return updated_node


# Register the command
register_command(ChangeValueToReferenceCommand)
