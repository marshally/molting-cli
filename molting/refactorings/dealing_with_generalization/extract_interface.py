"""Extract Interface refactoring - create a Protocol interface for common methods."""

import ast
from pathlib import Path
from typing import Optional

from molting.core.refactoring_base import RefactoringBase


class ExtractInterface(RefactoringBase):
    """Extract common methods from a class into a Protocol interface."""

    def __init__(
        self,
        file_path: str,
        target: str,
        methods: str,
        name: str,
    ):
        """Initialize the ExtractInterface refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target class name to extract interface from
            methods: Comma-separated list of method names to extract
            name: Name of the new interface (Protocol) to create
        """
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text()
        self.target_class = target
        self.methods_to_extract = [m.strip() for m in methods.split(",")]
        self.interface_name = name

    def apply(self, source: str) -> str:
        """Apply the extract interface refactoring to source code.

        Creates a Protocol with the specified methods and inserts it before
        the target class.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with new Protocol interface created
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        target_class_node = self.find_class_def(tree, self.target_class)
        if not target_class_node:
            raise ValueError(f"Target class '{self.target_class}' not found")

        extracted_methods = self._extract_methods(target_class_node)

        for method_name in self.methods_to_extract:
            if method_name not in extracted_methods:
                raise ValueError(
                    f"Method '{method_name}' not found in class '{self.target_class}'"
                )

        protocol_class = self._create_protocol(extracted_methods)

        self._ensure_protocol_import(tree)

        target_class_index = None
        for i, node in enumerate(tree.body):
            if isinstance(node, ast.ClassDef) and node.name == self.target_class:
                target_class_index = i
                break

        if target_class_index is not None:
            tree.body.insert(target_class_index, protocol_class)

        ast.fix_missing_locations(tree)

        return ast.unparse(tree)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = ast.parse(source)

            target_class = self.find_class_def(tree, self.target_class)
            if not target_class:
                return False

            for method_name in self.methods_to_extract:
                found = False
                for item in target_class.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        found = True
                        break
                if not found:
                    return False

            return True
        except (SyntaxError, AttributeError, ValueError):
            return False

    def _extract_methods(self, class_node: ast.ClassDef) -> dict:
        """Extract method definitions from a class.

        Args:
            class_node: The ClassDef AST node

        Returns:
            Dictionary mapping method names to FunctionDef nodes
        """
        methods = {}
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name != "__init__":
                methods[item.name] = item
        return methods

    def _create_protocol(self, extracted_methods: dict) -> ast.ClassDef:
        """Create a Protocol interface with stub methods.

        Args:
            extracted_methods: Dictionary of method name to FunctionDef

        Returns:
            A ClassDef AST node for the Protocol interface
        """
        body: list[ast.stmt] = []
        for method_name in self.methods_to_extract:
            if method_name not in extracted_methods:
                continue

            original_method = extracted_methods[method_name]
            return_annotation = self._infer_return_type(method_name, original_method)

            stub_method = ast.FunctionDef(
                name=method_name,
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self", annotation=None)],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[ast.Expr(value=ast.Constant(value=...))],
                decorator_list=[],
                returns=return_annotation,
            )
            body.append(stub_method)

        if not body:
            body = [ast.Pass()]

        protocol_class = ast.ClassDef(
            name=self.interface_name,
            bases=[ast.Name(id="Protocol", ctx=ast.Load())],
            keywords=[],
            body=body,
            decorator_list=[],
        )

        return protocol_class

    def _infer_return_type(
        self, method_name: str, method_node: ast.FunctionDef
    ) -> Optional[ast.expr]:
        """Infer return type annotation for a method.

        Args:
            method_name: Name of the method
            method_node: The FunctionDef AST node

        Returns:
            An AST annotation node or None
        """
        if method_name.startswith("get_"):
            if method_name == "get_rate":
                return ast.Name(id="float", ctx=ast.Load())
            elif method_name.startswith("get_"):
                return ast.Name(id="str", ctx=ast.Load())
        elif method_name.startswith("has_"):
            return ast.Name(id="bool", ctx=ast.Load())
        elif method_name.startswith("is_"):
            return ast.Name(id="bool", ctx=ast.Load())

        return None

    def _ensure_protocol_import(self, tree: ast.Module) -> None:
        """Ensure that 'from typing import Protocol' is present.

        Args:
            tree: The AST module to modify
        """
        has_protocol_import = False
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                for alias in node.names:
                    if alias.name == "Protocol":
                        has_protocol_import = True
                        break

        if not has_protocol_import:
            import_node = ast.ImportFrom(
                module="typing",
                names=[ast.alias(name="Protocol", asname=None)],
                level=0,
            )
            tree.body.insert(0, import_node)
