"""Change Bidirectional Association to Unidirectional refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, parse_target

# Method name constants
INIT_METHOD_NAME = "__init__"


class ChangeBidirectionalAssociationToUnidirectionalCommand(BaseCommand):
    """Command to change bidirectional association to unidirectional."""

    name = "change-bidirectional-association-to-unidirectional"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for "
                "change-bidirectional-association-to-unidirectional: 'target'"
            )

    def execute(self) -> None:
        """Apply change-bidirectional-association-to-unidirectional refactoring.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ChangeBidirectionalAssociationToUnidirectionalTransformer(
            class_name, field_name
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ChangeBidirectionalAssociationToUnidirectionalTransformer(cst.CSTTransformer):
    """Transforms bidirectional association to unidirectional."""

    def __init__(self, class_name: str, field_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the back reference (e.g., 'Customer')
            field_name: Name of the back reference field (e.g., '_orders')
        """
        self.class_name = class_name
        self.field_name = field_name
        self.forward_class_name: str | None = None

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Transform the module to remove bidirectional association."""
        # First pass: find the forward class and parameter name
        target_class = find_class_in_module(original_node, self.class_name)
        self._extract_forward_class_info(target_class)

        # Transform module
        new_statements: list[cst.BaseStatement] = []
        for stmt in updated_node.body:
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.class_name:
                    new_statements.append(self._modify_back_reference_class(stmt))
                elif self.forward_class_name and stmt.name.value == self.forward_class_name:
                    new_statements.append(self._modify_forward_class(stmt))
                else:
                    new_statements.append(stmt)
            else:
                new_statements.append(stmt)

        return updated_node.with_changes(body=tuple(new_statements))

    def _extract_forward_class_info(self, class_def: cst.ClassDef | None) -> None:
        """Extract the forward class name from the back reference class.

        Args:
            class_def: The back reference class definition to analyze
        """
        if class_def is None or not isinstance(class_def.body, cst.IndentedBlock):
            return

        # Look for add/remove methods to determine the forward class
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                method_name = stmt.name.value
                # Method names are like add_order, remove_order
                if method_name.startswith("add_"):
                    # Extract the singular form (e.g., 'order' from 'add_order')
                    singular = method_name[4:]  # Remove 'add_'
                    # Capitalize to get class name (e.g., 'Order' from 'order')
                    self.forward_class_name = singular.capitalize()
                    break

    def _modify_back_reference_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the back reference class to remove the back pointer.

        Args:
            class_def: The class definition

        Returns:
            Modified class definition (empty with pass)
        """
        # Remove all content except pass statement
        return class_def.with_changes(
            body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
        )

    def _modify_forward_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the forward class to simplify the bidirectional association.

        Args:
            class_def: The class definition

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []

        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == INIT_METHOD_NAME:
                new_body.append(self._simplify_init(stmt))
            elif isinstance(stmt, cst.FunctionDef) and stmt.name.value.startswith("set_"):
                # Remove setter methods
                continue
            else:
                new_body.append(stmt)

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _simplify_init(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Simplify __init__ to just assign the forward reference.

        Args:
            init_method: The __init__ method

        Returns:
            Simplified __init__ method
        """
        # Get the parameter name from original init (the second parameter after self)
        params = init_method.params
        param_name = "customer"  # Default

        if len(params.params) > 1:
            # Get the actual parameter name (should be like 'customer')
            second_param = params.params[1]
            if isinstance(second_param.name, cst.Name):
                param_name = second_param.name.value

        # Create simple assignment: self.customer = customer
        simple_assignment = cst.SimpleStatementLine(
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
                    value=cst.Name(param_name),
                )
            ]
        )

        return init_method.with_changes(body=cst.IndentedBlock(body=[simple_assignment]))


# Register the command
register_command(ChangeBidirectionalAssociationToUnidirectionalCommand)
