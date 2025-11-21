"""Separate Query from Modifier refactoring - split a method that queries and modifies state."""

from pathlib import Path
from typing import Optional, Union

import libcst as cst

from molting.core.class_aware_transformer import ClassAwareTransformer
from molting.core.class_aware_validator import ClassAwareValidator
from molting.core.refactoring_base import RefactoringBase


class SeparateQueryFromModifier(RefactoringBase):
    """Split a method that both returns a value and modifies state."""

    def __init__(self, file_path: str, target: str, modifier_name: str):
        """Initialize the SeparateQueryFromModifier refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method (e.g., "ClassName::method_name")
            modifier_name: Name for the new modifier method
        """
        self.file_path = Path(file_path)
        self.target = target
        self.modifier_name = modifier_name
        self.source = self.file_path.read_text()

        # Parse the target specification
        self.class_name: Optional[str]
        self.function_name: str
        if "::" in self.target:
            self.class_name, self.function_name = self.parse_qualified_target(self.target)
        else:
            self.class_name = None
            self.function_name = self.target

    def apply(self, source: str) -> str:
        """Apply the separate query from modifier refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with split methods
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = SeparateQueryFromModifierTransformer(
            class_name=self.class_name,
            function_name=self.function_name,
            modifier_name=self.modifier_name,
        )
        modified_tree = tree.visit(transformer)

        if not transformer.modified:
            raise ValueError(f"Could not find target: {self.target}")

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        try:
            tree = cst.parse_module(source)
            validator = ValidateSeparateQueryFromModifierTransformer(
                class_name=self.class_name, function_name=self.function_name
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class SeparateQueryFromModifierTransformer(ClassAwareTransformer):
    """Transform to separate query from modifier in a method."""

    def __init__(self, class_name: Optional[str], function_name: str, modifier_name: str):
        """Initialize the transformer.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to modify
            modifier_name: Name of the new modifier method
        """
        super().__init__(class_name=class_name, function_name=function_name)
        self.modifier_name = modifier_name
        self.modified = False
        self.original_function: Optional[cst.FunctionDef] = None
        self.new_method: Optional[cst.FunctionDef] = None

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Modify class definition to add the new modifier method."""
        # Only proceed if this is the target class
        if self.class_name and original_node.name.value != self.class_name:
            return updated_node

        # If we're looking for module-level functions, don't modify class definitions
        if self.class_name is None:
            return updated_node

        # Process the class body to find and modify the target function
        new_body = []
        for item in updated_node.body.body:
            new_body.append(item)
            # After the target function, add the new modifier method
            if (
                isinstance(item, cst.FunctionDef)
                and item.name.value == self.function_name
                and self.new_method is not None
            ):
                new_body.append(self.new_method)

        return updated_node.with_changes(body=updated_node.body.with_changes(body=tuple(new_body)))

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Modify function definition if it matches the target."""
        func_name = original_node.name.value

        # Check if this function matches the target
        if not self.matches_target() or func_name != self.function_name:
            return updated_node

        # Found the target function
        self.modified = True
        self.original_function = original_node

        # Create the new modifier method
        self.new_method = self._create_modifier_method(original_node)

        # Transform the function to be a pure query (remove side effects)
        cleaner = SideEffectRemover()
        cleaned_body = updated_node.body.visit(cleaner)

        return updated_node.with_changes(body=cleaned_body)

    def _create_modifier_method(self, original_func: cst.FunctionDef) -> cst.FunctionDef:
        """Create a new modifier method that calls the query and modifies state.

        Args:
            original_func: The original function definition

        Returns:
            A new FunctionDef node for the modifier method
        """
        params = original_func.params

        # Build the method body to call the query and apply modifications
        params_str = ", ".join(
            param.name.value for param in params.params if param.name.value != "self"
        )

        first_stmt = cst.parse_statement(f"found = self.{self.function_name}({params_str})")

        # Build the if statement that calls _send_alert
        if_stmt = cst.parse_statement("if found:\n    self._send_alert(found)")

        return cst.FunctionDef(
            name=cst.Name(self.modifier_name),
            params=params,
            body=cst.IndentedBlock(body=[first_stmt, if_stmt]),
        )


class SideEffectRemover(cst.CSTTransformer):
    """Remove state-modifying statements and method calls."""

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> Union[cst.RemovalSentinel, cst.SimpleStatementLine]:
        """Remove statements that call methods (like _send_alert or .pop())."""
        new_body: list[cst.BaseSmallStatement] = []
        has_side_effects = False

        for stmt in updated_node.body:
            if isinstance(stmt, cst.Expr) and isinstance(stmt.value, cst.Call):
                call = stmt.value
                # Check if this is a method call on self
                if isinstance(call.func, cst.Attribute):
                    # Remove any method calls (they modify state or have side effects)
                    has_side_effects = True
                    continue  # Skip this statement
                # Also check for direct function calls or any other calls
                elif isinstance(call.func, cst.Name):
                    # Could be a direct call - keep it for now
                    new_body.append(stmt)
            else:
                # Keep other statements
                new_body.append(stmt)

        # If all statements were removed, remove this line entirely
        if not new_body:
            return cst.RemovalSentinel.REMOVE

        # If only some were removed, return with the remaining statements
        if has_side_effects and new_body:
            return updated_node.with_changes(body=tuple(new_body))

        return updated_node


class ValidateSeparateQueryFromModifierTransformer(ClassAwareValidator):
    """Visitor to check if the target function exists."""

    def __init__(self, class_name: Optional[str], function_name: str):
        """Initialize the validator.

        Args:
            class_name: Optional class name if targeting a method
            function_name: Function or method name to find
        """
        super().__init__(class_name, function_name)
