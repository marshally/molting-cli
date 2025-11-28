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
    """Transforms module by adding a factory function and updating call sites."""

    def __init__(self, class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to create factory for
        """
        self.class_name = class_name
        self.factory_name = f"create_{class_name.lower()}"
        self.found_class = False
        self.init_params: list[cst.Param] = []
        self.class_insert_position: int | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to extract __init__ parameters."""
        if node.name.value == self.class_name:
            self.found_class = True
            # Find __init__ and extract its parameters
            if isinstance(node.body, cst.IndentedBlock):
                for stmt in node.body.body:
                    if isinstance(stmt, cst.FunctionDef):
                        if stmt.name.value == "__init__":
                            # Get params excluding 'self'
                            self.init_params = [
                                p
                                for p in stmt.params.params
                                if not (isinstance(p.name, cst.Name) and p.name.value == "self")
                            ]
                            break
        return True

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:  # noqa: N802
        """Replace constructor calls with factory function calls."""
        # Check if this is a call to the target class constructor
        if isinstance(updated_node.func, cst.Name):
            if updated_node.func.value == self.class_name:
                # Replace ClassName(...) with create_classname(...)
                return updated_node.with_changes(func=cst.Name(self.factory_name))
        return updated_node

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add factory function after the class definition."""
        if not self.found_class:
            return updated_node

        # Find where to insert the factory function (after the class definition)
        new_body: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            new_body.append(stmt)
            # Insert factory after the target class
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.class_name:
                factory_func = self._create_factory_function()
                new_body.append(factory_func)

        return updated_node.with_changes(body=new_body)

    def _create_factory_function(self) -> cst.FunctionDef:
        """Create the factory function.

        Returns:
            A function definition node
        """
        # Create parameter list from __init__ params
        if self.init_params:
            # Use the first param name from __init__
            param_name = (
                self.init_params[0].name.value
                if isinstance(self.init_params[0].name, cst.Name)
                else "arg"
            )
        else:
            param_name = "arg"

        # Create: return ClassName(param)
        return_stmt = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Call(
                        func=cst.Name(self.class_name),
                        args=[cst.Arg(value=cst.Name(param_name))],
                    )
                )
            ]
        )

        return cst.FunctionDef(
            name=cst.Name(self.factory_name),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name(param_name)),
                ]
            ),
            body=cst.IndentedBlock(body=[return_stmt]),
            leading_lines=[
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            ],
        )


# Register the command
register_command(ReplaceConstructorWithFactoryFunctionCommand)
