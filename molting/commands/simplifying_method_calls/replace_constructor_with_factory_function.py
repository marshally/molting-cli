"""Replace Constructor with Factory Function refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class ReplaceConstructorWithFactoryFunctionCommand(BaseCommand):
    """Command to replace constructor with a factory function."""

    name = "replace-constructor-with-factory-function"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-constructor-with-factory-function refactoring using libCST.

        Raises:
            ValueError: If class or method not found or target format is invalid
        """
        target = self.params["target"]
        class_name, method_name = parse_target(target, expected_parts=2)

        if method_name != "__init__":
            raise ValueError(f"Target must be a constructor (__init__), got: {method_name}")

        # Read file
        source_code = self.file_path.read_text()

        # Parse and transform
        module = cst.parse_module(source_code)
        transformer = ReplaceConstructorWithFactoryFunctionTransformer(class_name)
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ReplaceConstructorWithFactoryFunctionTransformer(cst.CSTTransformer):
    """Transforms module by adding a factory function for a class."""

    def __init__(self, class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to create factory for
        """
        self.class_name = class_name
        self.class_constants: list[str] = []
        self.found_class = False

    def _collect_class_constants(self, class_body: cst.BaseSuite) -> list[str]:
        """Collect constant names from class body.

        Args:
            class_body: The class body to search

        Returns:
            List of constant names
        """
        constants: list[str] = []
        # BaseSuite can be IndentedBlock or SimpleStatementSuite
        if isinstance(class_body, cst.IndentedBlock):
            statements = class_body.body
        else:
            # SimpleStatementSuite doesn't have constants typically
            return constants

        for stmt in statements:
            if isinstance(stmt, cst.SimpleStatementLine):
                for inner in stmt.body:
                    if isinstance(inner, cst.Assign):
                        for target in inner.targets:
                            if isinstance(target.target, cst.Name):
                                constants.append(target.target.value)
        return constants

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Visit class definition to collect constants.

        Args:
            node: The class definition node
        """
        if node.name.value == self.class_name:
            self.found_class = True
            self.class_constants = self._collect_class_constants(node.body)

    def _create_condition(self, constant: str, param_name: str) -> cst.Comparison:
        """Create a condition that tests parameter against constant name.

        Args:
            constant: The constant name to test
            param_name: The parameter name to compare

        Returns:
            A comparison node
        """
        return cst.Comparison(
            left=cst.Name(param_name),
            comparisons=[
                cst.ComparisonTarget(
                    operator=cst.Equal(),
                    comparator=cst.SimpleString(f'"{constant}"'),
                )
            ],
        )

    def _create_return_statement(self, constant: str) -> cst.SimpleStatementLine:
        """Create a return statement that instantiates the class with a constant.

        Args:
            constant: The constant name to use

        Returns:
            A return statement node
        """
        return cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Call(
                        func=cst.Name(self.class_name),
                        args=[
                            cst.Arg(
                                value=cst.Attribute(
                                    value=cst.Name(self.class_name),
                                    attr=cst.Name(constant),
                                )
                            )
                        ],
                    )
                )
            ]
        )

    def _build_if_chain(self, param_name: str) -> cst.If | None:
        """Build if-elif chain for all constants.

        Args:
            param_name: The parameter name for the factory function

        Returns:
            The if chain or None if no constants
        """
        if_chain = None
        for constant in reversed(self.class_constants):
            condition = self._create_condition(constant, param_name)
            return_stmt = self._create_return_statement(constant)

            if if_chain is None:
                # Last condition (no else)
                if_chain = cst.If(
                    test=condition,
                    body=cst.IndentedBlock(body=[return_stmt]),
                    orelse=None,
                )
            else:
                # Wrap previous chain as orelse
                if_chain = cst.If(
                    test=condition,
                    body=cst.IndentedBlock(body=[return_stmt]),
                    orelse=if_chain,
                )
        return if_chain

    def _create_factory_function(
        self, factory_name: str, param_name: str, if_chain: cst.If | None
    ) -> cst.FunctionDef:
        """Create factory function definition.

        Args:
            factory_name: Name of the factory function
            param_name: Name of the parameter
            if_chain: The if-elif chain for the body

        Returns:
            A function definition node
        """
        return cst.FunctionDef(
            name=cst.Name(factory_name),
            params=cst.Parameters(params=[cst.Param(name=cst.Name(param_name))]),
            body=(
                cst.IndentedBlock(body=[if_chain])
                if if_chain
                else cst.SimpleStatementSuite(body=[cst.Pass()])
            ),
            leading_lines=[
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            ],
        )

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add factory function after module transformation.

        Args:
            original_node: The original module
            updated_node: The updated module

        Returns:
            Module with factory function added
        """
        if not self.found_class:
            return updated_node

        if not self.class_constants:
            return updated_node

        factory_name = f"create_{self.class_name.lower()}"
        param_name = "employee_type"

        if_chain = self._build_if_chain(param_name)
        factory_func = self._create_factory_function(factory_name, param_name, if_chain)

        new_body = list(updated_node.body) + [factory_func]
        return updated_node.with_changes(body=new_body)


# Register the command
register_command(ReplaceConstructorWithFactoryFunctionCommand)
