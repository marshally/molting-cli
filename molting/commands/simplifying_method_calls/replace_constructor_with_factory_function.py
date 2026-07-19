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

        This supports both single-file and multi-file refactoring:
        - If the class definition is in the file, adds the factory function
        - If the file imports the class, updates the import and constructor calls
        - If the file only has constructor calls, updates them

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

        # Only write if changes were made
        if modified_tree.code != source_code:
            self.file_path.write_text(modified_tree.code)


class ReplaceConstructorWithFactoryFunctionTransformer(cst.CSTTransformer):
    """Transforms module by adding a factory function and updating call sites.

    This transformer supports multi-file refactoring by:
    1. Adding the factory function if the class is defined in this file
    2. Updating imports if the class is imported from another module
    3. Replacing all constructor calls with factory function calls
    """

    def __init__(self, class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class to create factory for
        """
        self.class_name = class_name
        self.factory_name = f"create_{class_name.lower()}"
        self.found_class = False
        self.init_params: list[cst.Param] = []
        self.has_constructor_calls = False
        self.imports_class = False

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
                self.has_constructor_calls = True
                # Replace ClassName(...) with create_classname(...)
                return updated_node.with_changes(func=cst.Name(self.factory_name))
        return updated_node

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Update imports to add factory function if class is imported.

        If a file imports the class, we need to also import the factory function.
        Example: from employee import Employee -> from employee import Employee, create_employee
        """
        if not isinstance(updated_node.names, (list, tuple)):
            # Skip star imports and other special cases
            return updated_node

        # Check if this import includes our class
        names_list = list(updated_node.names)
        has_class = any(
            isinstance(name, cst.ImportAlias)
            and isinstance(name.name, cst.Name)
            and name.name.value == self.class_name
            for name in names_list
        )

        if not has_class:
            return updated_node

        self.imports_class = True

        # Check if factory is already imported
        has_factory = any(
            isinstance(name, cst.ImportAlias)
            and isinstance(name.name, cst.Name)
            and name.name.value == self.factory_name
            for name in names_list
        )

        if not has_factory:
            # Add factory to imports
            new_names = names_list + [cst.ImportAlias(name=cst.Name(self.factory_name))]
            return updated_node.with_changes(names=new_names)

        return updated_node

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add factory function after the class definition (if class is in this file)."""
        # Only add factory function if the class is defined in this file
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
        # Create parameter list and args from all __init__ params
        factory_params: list[cst.Param] = []
        call_args: list[cst.Arg] = []

        for param in self.init_params:
            if isinstance(param.name, cst.Name):
                param_name = param.name.value
                # Create factory parameter (without default values or annotations for simplicity)
                factory_params.append(cst.Param(name=cst.Name(param_name)))
                # Create corresponding argument for constructor call
                call_args.append(cst.Arg(value=cst.Name(param_name)))

        # Create: return ClassName(arg1, arg2, ...)
        return_stmt = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.Call(
                        func=cst.Name(self.class_name),
                        args=call_args,
                    )
                )
            ]
        )

        return cst.FunctionDef(
            name=cst.Name(self.factory_name),
            params=cst.Parameters(params=factory_params),
            body=cst.IndentedBlock(body=[return_stmt]),
            leading_lines=[
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
                cst.EmptyLine(whitespace=cst.SimpleWhitespace("")),
            ],
        )


# Register the command
register_command(ReplaceConstructorWithFactoryFunctionCommand)
