"""Extract Function refactoring command."""

import libcst as cst
from libcst import metadata

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target_with_line
from molting.core.code_generation_utils import create_parameter


class ExtractFunctionCommand(BaseCommand):
    """Command to extract code into a module-level function."""

    name = "extract-function"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply extract-function refactoring using libCST.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        new_function_name = self.params["name"]

        # Parse target and line number using shared utility
        class_name, method_name, line_spec = parse_target_with_line(target)
        # Extract line number from line_spec (e.g., "L4" -> 4)
        line_number = int(line_spec[1:])

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

    def _get_first_non_self_parameter(self, function_def: cst.FunctionDef) -> str:
        """Extract the first non-self parameter name from a method.

        Args:
            function_def: The function definition to extract from

        Returns:
            The name of the first non-self parameter, or "data" as default
        """
        if not function_def.params.params:
            return "data"

        for param in function_def.params.params:
            if param.name.value != "self":
                return param.name.value

        return "data"

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

            param_name = self._get_first_non_self_parameter(updated_node)

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
            params=cst.Parameters(params=[create_parameter(param_name)]),
            body=cst.IndentedBlock(body=[return_stmt]),
        )

        # Add the function at the beginning of the module
        new_body = [new_function, cst.EmptyLine(indent=False), cst.EmptyLine(indent=False)]
        new_body.extend(updated_node.body)

        return updated_node.with_changes(body=tuple(new_body))


# Register the command
register_command(ExtractFunctionCommand)
