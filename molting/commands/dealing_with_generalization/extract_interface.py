"""Extract Interface refactoring command."""

import ast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class ExtractInterfaceCommand(BaseCommand):
    """Command to extract an interface (Protocol) from a class."""

    name = "extract-interface"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        required = ["target", "methods", "name"]
        for param in required:
            if param not in self.params:
                raise ValueError(f"Missing required parameter for extract-interface: '{param}'")

    def execute(self) -> None:
        """Apply extract-interface refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        methods_str = self.params["methods"]
        interface_name = self.params["name"]

        # Parse the methods string (comma-separated list)
        methods = [m.strip() for m in methods_str.split(",")]

        # Read file
        source_code = self.file_path.read_text()

        # First, parse with ast to find return types
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}") from e

        method_types = self._extract_method_return_types(tree, methods)

        # Now parse with libcst for transformation
        module = cst.parse_module(source_code)

        # Create the Protocol interface with type hints
        protocol_class = self._create_protocol_interface(interface_name, methods, method_types)

        # Add typing import if not present
        module = self._add_typing_import(module)

        # Add the protocol at the beginning (after imports)
        new_module = self._insert_protocol(module, protocol_class)

        # Write back
        self.file_path.write_text(new_module.code)

    def _extract_method_return_types(self, tree: ast.Module, methods: list[str]) -> dict[str, str]:
        """Extract return type hints from methods using ast analysis.

        Args:
            tree: The AST module
            methods: List of method names to extract

        Returns:
            Dictionary mapping method names to return type strings
        """
        method_types: dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name in methods:
                        # Try to infer type from return annotation
                        if item.returns:
                            method_types[item.name] = ast.unparse(item.returns)
                        else:
                            # Try to infer from return statements
                            inferred_type = self._infer_return_type(item)
                            if inferred_type:
                                method_types[item.name] = inferred_type

        # Set defaults for methods we couldn't infer types for
        for method in methods:
            if method not in method_types:
                method_types[method] = "Any"

        return method_types

    def _infer_return_type(self, func: ast.FunctionDef) -> str | None:
        """Try to infer return type from function implementation.

        Args:
            func: The function definition

        Returns:
            Inferred type string or None
        """
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and node.value:
                # Simple heuristics for common types
                if isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, bool):
                        return "bool"
                    elif isinstance(node.value.value, (int, float)):
                        return "float"
                    elif isinstance(node.value.value, str):
                        return "str"
                elif isinstance(node.value, ast.BoolOp):
                    return "bool"
                elif isinstance(node.value, ast.Compare):
                    return "bool"
                elif isinstance(node.value, ast.Attribute):
                    # Returning an attribute - likely a numeric or complex type
                    # Use float as a reasonable default for most data
                    return "float"
                elif isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Attribute):
                        if node.value.func.attr == "get":
                            return "Any"
        return None

    def _create_protocol_interface(
        self, name: str, methods: list[str], method_types: dict[str, str]
    ) -> cst.ClassDef:
        """Create a Protocol interface class with type hints.

        Args:
            name: Name of the interface
            methods: List of method names to extract
            method_types: Dictionary of method names to return types

        Returns:
            A ClassDef node for the Protocol
        """
        # Create method stubs with ellipsis bodies and type hints
        method_stubs: list[cst.BaseStatement] = []
        for i, method_name in enumerate(methods):
            # Get return type, default to Any
            return_type = method_types.get(method_name, "Any")

            # Parse return type
            returns = cst.Annotation(annotation=cst.parse_expression(return_type))

            # Create: def method_name(self) -> type: ...
            stub = cst.FunctionDef(
                name=cst.Name(method_name),
                params=cst.Parameters(
                    params=[cst.Param(name=cst.Name("self"))],
                ),
                returns=returns,
                body=cst.SimpleStatementSuite(body=[cst.Expr(value=cst.Ellipsis())]),
            )
            method_stubs.append(stub)

            # Add blank line after each method (except the last one)
            if i < len(methods) - 1:
                method_stubs.append(cst.EmptyLine())

        # Create the Protocol class inheriting from Protocol
        protocol = cst.ClassDef(
            name=cst.Name(name),
            bases=[cst.Arg(value=cst.Name("Protocol"))],
            body=cst.IndentedBlock(body=method_stubs),
        )

        return protocol

    def _add_typing_import(self, module: cst.Module) -> cst.Module:
        """Add 'from typing import Protocol' if not already present.

        Args:
            module: The module to modify

        Returns:
            The modified module
        """
        # Check if typing import already exists
        has_typing_import = False
        for stmt in module.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.ImportFrom):
                        if isinstance(item.module, cst.Name):
                            if item.module.value == "typing":
                                has_typing_import = True
                                break

        if has_typing_import:
            return module

        # Add the import at the beginning
        import_stmt = cst.SimpleStatementLine(
            body=[
                cst.ImportFrom(
                    module=cst.Name("typing"),
                    names=[cst.ImportAlias(name=cst.Name("Protocol"))],
                )
            ]
        )

        # Insert after any existing imports at the top
        new_body = [import_stmt] + list(module.body)

        return module.with_changes(body=new_body)

    def _insert_protocol(self, module: cst.Module, protocol: cst.ClassDef) -> cst.Module:
        """Insert the protocol class into the module.

        Args:
            module: The module to modify
            protocol: The Protocol class to insert

        Returns:
            The modified module
        """
        # Find the position to insert (after imports)
        insert_pos = 0
        for i, stmt in enumerate(module.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                insert_pos = i + 1
            elif isinstance(stmt, cst.EmptyLine):
                continue
            else:
                break

        # Create blank line separator
        blank_line = cst.EmptyLine()

        # Insert the protocol
        new_body = (
            list(module.body[:insert_pos])
            + [blank_line, blank_line]
            + [protocol]
            + [blank_line]
            + list(module.body[insert_pos:])
        )

        return module.with_changes(body=new_body)


# Register the command
register_command(ExtractInterfaceCommand)
