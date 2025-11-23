"""Extract Function refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target

# Target format constants
TARGET_SEPARATOR = "#"
LINE_PREFIX = "L"


class ExtractFunctionCommand(BaseCommand):
    """Command to extract code into a module-level function."""

    name = "extract-function"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def _parse_target_specification(self, target: str) -> tuple[str, str, str]:
        """Parse target format into class::method and line components.

        Args:
            target: Target string in format "ClassName::method_name#L4"

        Returns:
            Tuple of (class_name, method_name, line_number)

        Raises:
            ValueError: If target format is invalid
        """
        # Parse target format: "ClassName::method_name#L4"
        parts = target.split(TARGET_SEPARATOR)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid target format '{target}'. Expected 'ClassName::method_name#L4'"
            )

        class_method = parts[0]
        line_spec = parts[1]

        # Parse class and method name
        try:
            class_name, method_name = parse_target(class_method, expected_parts=2)
        except ValueError as e:
            raise ValueError(f"Invalid class::method format in target '{target}': {e}") from e

        return class_name, method_name, line_spec

    def _parse_line_number(self, line_spec: str) -> int:
        """Parse line number string into integer.

        Args:
            line_spec: Line number in format "L4"

        Returns:
            Line number as integer

        Raises:
            ValueError: If line number format is invalid
        """
        if not line_spec.startswith(LINE_PREFIX):
            raise ValueError(f"Invalid line format '{line_spec}'. Expected 'L4'")

        try:
            line_number = int(line_spec[1:])
        except ValueError as e:
            raise ValueError(f"Invalid line number in '{line_spec}': {e}") from e

        return line_number

    def execute(self) -> None:
        """Apply extract-function refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        new_function_name = self.params["name"]

        # Parse target and line number
        class_name, method_name, line_spec = self._parse_target_specification(target)
        line_number = self._parse_line_number(line_spec)

        # Read file
        source_code = self.file_path.read_text()

        # First pass: collect the expression to extract
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        collector = ExpressionCollector(class_name, method_name, line_number)
        wrapper.visit(collector)

        if collector.extracted_expression is None:
            raise ValueError(f"Could not find expression at line {line_number}")

        # Second pass: apply transformation
        wrapper = metadata.MetadataWrapper(cst.parse_module(source_code))
        transformer = ExtractFunctionTransformer(
            class_name,
            method_name,
            new_function_name,
            line_number,
            collector.extracted_expression,
        )
        modified_tree = wrapper.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class ExpressionCollector(cst.CSTVisitor):
    """Collector to find the expression to extract."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(self, class_name: str, method_name: str, line_number: int) -> None:
        """Initialize the collector.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to extract code from
            line_number: Line number of expression to extract (1-indexed)
        """
        self.method_name = method_name
        self.line_number = line_number
        self.extracted_expression: cst.BaseExpression | None = None
        self.in_target_method = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to find target method."""
        if node.name.value == self.method_name:
            self.in_target_method = True

    def leave_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Leave function definition."""
        if node.name.value == self.method_name:
            self.in_target_method = False

    def visit_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:  # noqa: N802
        """Visit simple statement to check if it's on the target line."""
        if not self.in_target_method:
            return

        try:
            position = self.get_metadata(metadata.PositionProvider, node)
            if position.start.line == self.line_number:
                # Extract the right-hand side of an assignment
                for stmt in node.body:
                    if isinstance(stmt, cst.Assign):
                        self.extracted_expression = stmt.value
                        break
        except KeyError:
            pass


class ExtractFunctionTransformer(cst.CSTTransformer):
    """Transforms a module by extracting a function."""

    METADATA_DEPENDENCIES = (metadata.PositionProvider,)

    def __init__(
        self,
        class_name: str,
        method_name: str,
        new_function_name: str,
        line_number: int,
        extracted_expression: cst.BaseExpression,
    ) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the method
            method_name: Name of the method to extract code from
            new_function_name: Name of the new extracted function
            line_number: Line number of expression to extract (1-indexed)
            extracted_expression: The expression to extract
        """
        self.method_name = method_name
        self.new_function_name = new_function_name
        self.extracted_expression = extracted_expression
        self.in_target_method = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:  # noqa: N802
        """Visit function definition to find target method."""
        if node.name.value == self.method_name:
            self.in_target_method = True

    def leave_FunctionDef(  # noqa: N802
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Transform the method to call the extracted function."""
        if original_node.name.value == self.method_name:
            self.in_target_method = False

            # Find the parameter name from the method signature (skip 'self')
            param_name = "data"
            if updated_node.params.params:
                # Skip 'self' parameter - get the first non-self parameter
                for param in updated_node.params.params:
                    if param.name.value != "self":
                        param_name = param.name.value
                        break

            # Create a return statement with the function call
            function_call = cst.Call(
                func=cst.Name(self.new_function_name), args=[cst.Arg(value=cst.Name(param_name))]
            )
            return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=function_call)])

            # Replace the entire method body with just the return statement
            new_body = cst.IndentedBlock(body=[return_stmt])
            return updated_node.with_changes(body=new_body)

        return updated_node

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add the extracted function to the module."""
        if self.extracted_expression is None:
            return updated_node

        # Create the new function
        param_name = "data"

        # Create return statement
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=self.extracted_expression)])

        # Create function definition
        new_function = cst.FunctionDef(
            name=cst.Name(self.new_function_name),
            params=cst.Parameters(params=[cst.Param(name=cst.Name(param_name))]),
            body=cst.IndentedBlock(body=[return_stmt]),
        )

        # Add the function at the beginning of the module
        new_body = [new_function, cst.EmptyLine(indent=False), cst.EmptyLine(indent=False)]
        new_body.extend(updated_node.body)

        return updated_node.with_changes(body=tuple(new_body))


# Register the command
register_command(ExtractFunctionCommand)
