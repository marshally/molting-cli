"""Extract Interface refactoring command."""

import ast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_comma_separated_list
from molting.core.code_generation_utils import create_parameter
from molting.core.import_utils import ensure_import


class ExtractInterfaceCommand(BaseCommand):
    """Extract a Protocol interface from a subset of methods in a class.

    This refactoring creates a new Protocol (Python's equivalent to an interface)
    from a subset of methods that are commonly used by clients. It defines a contract
    that multiple classes can implement, reducing coupling between client code and
    concrete implementations while making it easier to write polymorphic code.

    **When to use:**
    - When multiple classes share a common set of methods that clients depend on
    - When you want to decouple client code from concrete class implementations
    - When you need to define a contract that different implementations should follow
    - When you have a class with both "public" methods used by clients and "private"
      helper methods that should not be part of the interface

    **Example:**

    Before:
        class BankAccount:
            def deposit(self, amount: float) -> None:
                self.balance += amount

            def withdraw(self, amount: float) -> None:
                self.balance -= amount

            def reset_balance(self) -> None:
                self.balance = 0

        def process_transaction(account: BankAccount) -> None:
            account.deposit(100)

    After:
        from typing import Protocol

        class BankAccountInterface(Protocol):
            def deposit(self, amount: float) -> None:
                ...

            def withdraw(self, amount: float) -> None:
                ...

        class BankAccount:
            def deposit(self, amount: float) -> None:
                self.balance += amount

            def withdraw(self, amount: float) -> None:
                self.balance -= amount

            def reset_balance(self) -> None:
                self.balance = 0

        def process_transaction(account: BankAccountInterface) -> None:
            account.deposit(100)
    """

    name = "extract-interface"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "methods", "name")

    def execute(self) -> None:
        """Apply extract-interface refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        methods_str = self.params["methods"]
        interface_name = self.params["name"]

        # Parse the methods string (comma-separated list)
        methods = parse_comma_separated_list(methods_str)

        # Read file
        source_code = self.file_path.read_text()

        # Check for name conflicts - if the interface name already exists, skip
        module = cst.parse_module(source_code)
        for stmt in module.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == interface_name:
                # Class with target name already exists, skip the refactoring
                return

        # First, parse with ast to find return types
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}") from e

        method_types, methods_found = self._extract_method_return_types(tree, methods)

        # Validate that at least one method was found
        if not methods_found:
            raise ValueError(f"Methods not found in class: {', '.join(methods)}")

        # Now parse with libcst for transformation
        module = cst.parse_module(source_code)

        # Create the Protocol interface with type hints
        protocol_class = self._create_protocol_interface(interface_name, methods, method_types)

        # Add typing import if not present
        module = ensure_import(module, "typing", ["Protocol"])

        # Add the protocol at the beginning (after imports)
        new_module = self._insert_protocol(module, protocol_class)

        # Write back
        self.file_path.write_text(new_module.code)

    def _extract_method_return_types(
        self, tree: ast.Module, methods: list[str]
    ) -> tuple[dict[str, str], set[str]]:
        """Extract return type hints from methods using ast analysis.

        Args:
            tree: The AST module
            methods: List of method names to extract

        Returns:
            Tuple of (dictionary mapping method names to return type strings,
                      set of method names that were found)
        """
        method_types: dict[str, str] = {}
        methods_found: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name in methods:
                        methods_found.add(item.name)
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

        return method_types, methods_found

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
                    params=[create_parameter("self")],
                ),
                returns=returns,
                body=cst.SimpleStatementSuite(body=[cst.Expr(value=cst.Ellipsis())]),
            )
            method_stubs.append(stub)

            # Add blank line after each method (except the last one)
            if i < len(methods) - 1:
                method_stubs.append(cst.EmptyLine())  # type: ignore[arg-type]

        # Create the Protocol class inheriting from Protocol
        protocol = cst.ClassDef(
            name=cst.Name(name),
            bases=[cst.Arg(value=cst.Name("Protocol"))],
            body=cst.IndentedBlock(body=method_stubs),
        )

        return protocol

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
