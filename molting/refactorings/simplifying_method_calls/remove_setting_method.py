"""Remove Setting Method refactoring - remove a setter method from a class."""

from pathlib import Path

import libcst as cst

from molting.core.class_aware_transformer import ClassAwareTransformer
from molting.core.class_aware_validator import ClassAwareValidator
from molting.core.refactoring_base import RefactoringBase


class RemoveSettingMethod(RefactoringBase):
    """Remove a setter method from a class."""

    def __init__(self, file_path: str, target: str):
        """Initialize the RemoveSettingMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target method (e.g., "ClassName::method_name")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.source = self.file_path.read_text()
        # Parse the target specification - must be "ClassName::method_name" format
        if "::" not in self.target:
            raise ValueError(
                f"Invalid target format: {self.target}. Expected 'ClassName::method_name'"
            )
        self.class_name, self.method_name = self.parse_qualified_target(self.target)

    def apply(self, source: str) -> str:
        """Apply the remove setting method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with setter method removed
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = RemoveSettingMethodTransformer(
            class_name=self.class_name, method_name=self.method_name
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
            validator = ValidateRemoveSettingMethodTransformer(
                class_name=self.class_name, method_name=self.method_name
            )
            tree.visit(validator)
            return validator.found
        except Exception:
            return False


class RemoveSettingMethodTransformer(ClassAwareTransformer):
    """Transform to remove a setter method from a class."""

    def __init__(self, class_name: str, method_name: str):
        """Initialize the transformer.

        Args:
            class_name: Class name containing the method
            method_name: Method name to remove
        """
        super().__init__(class_name=class_name, function_name=method_name)
        self.method_name = method_name
        self.modified = False

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Remove the setter method from the class body."""
        if original_node.name.value != self.class_name:
            return updated_node

        # Filter out the setter method
        new_body = []
        for statement in updated_node.body.body:
            if isinstance(statement, cst.FunctionDef):
                if statement.name.value == self.method_name:
                    # Check if this is a property setter
                    if self._has_setter_decorator(statement):
                        self.modified = True
                        continue  # Skip this property setter
                    elif self._is_simple_setter(statement):
                        self.modified = True
                        continue  # Skip this regular setter
            new_body.append(statement)

        if self.modified:
            return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))

        return updated_node

    def _has_setter_decorator(self, node: cst.FunctionDef) -> bool:
        """Check if the function has a @<method_name>.setter or @property.setter decorator."""
        for decorator in node.decorators:
            # Handle both @property.setter and @name.setter patterns
            if isinstance(decorator.decorator, cst.Attribute):
                attr = decorator.decorator
                # Check for pattern like @price.setter where price is our method name
                if (
                    isinstance(attr.attr, cst.Name)
                    and attr.attr.value == "setter"
                    and isinstance(attr.value, cst.Name)
                    and attr.value.value == self.method_name
                ):
                    return True
        return False

    def _is_simple_setter(self, node: cst.FunctionDef) -> bool:
        """Check if this is a simple setter method (not a property)."""
        # It's a simple setter if it doesn't have any decorators
        return len(node.decorators) == 0


class ValidateRemoveSettingMethodTransformer(ClassAwareValidator):
    """Visitor to check if the target method exists."""

    def __init__(self, class_name: str, method_name: str):
        """Initialize the validator.

        Args:
            class_name: Class name containing the method
            method_name: Method name to find
        """
        super().__init__(class_name, method_name)
