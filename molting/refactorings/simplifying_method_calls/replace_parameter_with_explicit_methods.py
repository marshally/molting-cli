"""Replace Parameter with Explicit Methods refactoring."""

from pathlib import Path
from typing import Optional, Sequence

import libcst as cst

from molting.core.class_aware_transformer import ClassAwareTransformer
from molting.core.class_aware_validator import ClassAwareValidator
from molting.core.refactoring_base import RefactoringBase


class ReplaceParameterWithExplicitMethods(RefactoringBase):
    """Replace a parameter that controls code path with separate explicit methods."""

    def __init__(self, file_path: str, target: str, parameter_name: Optional[str] = None):
        """Initialize the ReplaceParameterWithExplicitMethods refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method in format "ClassName::method_name::parameter_name" or "ClassName::method_name"
            parameter_name: The parameter to replace with explicit methods (can also be in target)
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()

        # Parse the target specification - format: "ClassName::method_name::parameter_name"
        parts = target.split("::")
        if len(parts) >= 3:
            # Format: ClassName::method_name::parameter_name
            self.class_name = parts[0]
            self.method_name = parts[1]
            self.parameter_name = parts[2]
        elif len(parts) == 2 and parameter_name:
            # Format: ClassName::method_name with separate parameter_name
            self.class_name = parts[0]
            self.method_name = parts[1]
            self.parameter_name = parameter_name
        else:
            raise ValueError(f"Invalid target format: {target}")

    def apply(self, source: str) -> str:
        """Apply the refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with explicit methods
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ReplaceParameterWithExplicitMethodsTransformer(
            class_name=self.class_name,
            function_name=self.method_name,
            parameter_name=self.parameter_name,
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
            validator = ValidateReplaceParameterWithExplicitMethodsTransformer(
                class_name=self.class_name,
                function_name=self.method_name,
                parameter_name=self.parameter_name,
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class ReplaceParameterWithExplicitMethodsTransformer(ClassAwareTransformer):
    """Transform to replace parameter with explicit methods."""

    def __init__(self, class_name: str, function_name: str, parameter_name: str):
        """Initialize the transformer.

        Args:
            class_name: Class name containing the method
            function_name: Method name to transform
            parameter_name: Parameter controlling code paths
        """
        super().__init__(class_name=class_name, function_name=function_name)
        self.parameter_name = parameter_name
        self.modified = False
        self.extracted_methods = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.RemovalSentinel | cst.FunctionDef | cst.FlattenSentinel:
        """Transform method if it matches the target."""
        # Check if this is the method we're looking for
        if not self.matches_target() or original_node.name.value != self.function_name:
            return updated_node

        # Check if the method has the parameter we're targeting
        params = original_node.params
        param_names = [p.name.value for p in params.params]

        if self.parameter_name not in param_names:
            return updated_node

        # Found the target method, extract explicit methods
        self.modified = True

        # Extract the parameter values from the if/elif chain
        method_variants = self._extract_method_variants(updated_node)

        # Create new methods without the parameter
        new_methods = self._create_explicit_methods(updated_node, method_variants)

        # Return the new methods as a flat sequence
        return cst.FlattenSentinel(new_methods)

    def _extract_method_variants(self, method_def: cst.FunctionDef) -> dict:
        """Extract variants from if/elif chain checking parameter.

        Args:
            method_def: The method definition to analyze

        Returns:
            Dictionary mapping parameter values to their method bodies
        """
        variants = {}

        # Get the function body
        if isinstance(method_def.body, cst.IndentedBlock):
            for stmt in method_def.body.body:
                if isinstance(stmt, cst.If):
                    # Extract the if/elif chain
                    self._extract_if_chain(stmt, variants)

        return variants

    def _extract_if_chain(self, if_stmt: cst.If, variants: dict) -> None:
        """Extract parameter values and bodies from if/elif chain.

        Args:
            if_stmt: The If statement to process
            variants: Dictionary to populate with variants
        """
        # Check the test condition for parameter equality
        test = if_stmt.test
        value = self._extract_parameter_value(test)

        if value:
            # Store the body for this variant
            variants[value] = if_stmt.body

        # Check for elif (which is represented as another If node in orelse)
        if if_stmt.orelse:
            if isinstance(if_stmt.orelse, cst.If):
                # This is an elif
                self._extract_if_chain(if_stmt.orelse, variants)
            elif isinstance(if_stmt.orelse, cst.IndentedBlock):
                # This is an else block
                for stmt in if_stmt.orelse.body:
                    if isinstance(stmt, cst.If):
                        self._extract_if_chain(stmt, variants)

    def _extract_parameter_value(self, test: cst.BaseExpression) -> Optional[str]:
        """Extract the parameter value from a comparison.

        Args:
            test: The test expression

        Returns:
            The parameter value (e.g., "height", "width") or None
        """
        # Handle: if name == "height":
        if isinstance(test, cst.Comparison):
            if len(test.comparisons) > 0:
                comparison = test.comparisons[0]
                if isinstance(comparison.operator, cst.Equal):
                    # Check left side
                    if isinstance(test.left, cst.Name):
                        if test.left.value == self.parameter_name:
                            # Get the string value from right side
                            right = comparison.comparator
                            if isinstance(right, cst.SimpleString):
                                # Remove quotes
                                value = right.value.strip("\"'")
                                return value

        return None

    def _create_explicit_methods(
        self, original_method: cst.FunctionDef, variants: dict
    ) -> Sequence[cst.FunctionDef]:
        """Create explicit methods from variants.

        Args:
            original_method: The original method definition
            variants: Dictionary of parameter values to bodies

        Returns:
            List of new method definitions
        """
        new_methods = []

        # Get parameters without the control parameter
        params = original_method.params
        new_params_list = []
        for param in params.params:
            if param.name.value != self.parameter_name:
                new_params_list.append(param)

        # Create a new method for each variant
        for value, body in variants.items():
            method_name = f"set_{value}"

            # Create new params tuple
            if new_params_list:
                new_params = params.with_changes(params=tuple(new_params_list))
            else:
                new_params = params.with_changes(params=tuple(new_params_list))

            # Create the new method
            new_method = cst.FunctionDef(
                name=cst.Name(method_name),
                params=new_params,
                body=body,
                leading_lines=original_method.leading_lines,
            )

            new_methods.append(new_method)

        return new_methods


class ValidateReplaceParameterWithExplicitMethodsTransformer(ClassAwareValidator):
    """Visitor to check if the target method exists."""

    def __init__(self, class_name: str, function_name: str, parameter_name: str):
        """Initialize the validator.

        Args:
            class_name: Class name containing the method
            function_name: Method name to find
            parameter_name: Parameter to validate
        """
        super().__init__(class_name, function_name)
        self.parameter_name = parameter_name
