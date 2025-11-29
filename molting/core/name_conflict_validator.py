"""Validator for detecting name conflicts when creating classes or constants.

This module provides a utility to check if a class name or constant name
already exists at module level before refactoring operations create them.
"""

import libcst as cst

from molting.core.visitors import ClassConflictChecker, ConstantConflictChecker


class NameConflictValidator:
    """Validates that class and constant names don't conflict at module level.

    This validator uses visitor patterns to detect existing classes and constants
    in the module, preventing accidental overwriting of existing code.

    Example:
        source = "class Customer: pass"
        validator = NameConflictValidator(source)
        validator.validate_class_name("Customer")  # Raises ValueError
        validator.validate_class_name("Order")     # Passes
    """

    def __init__(self, source_code: str) -> None:
        """Initialize the validator with source code.

        Args:
            source_code: The Python source code to analyze for conflicts
        """
        self.source_code = source_code
        self.module = cst.parse_module(source_code)

    def validate_class_name(self, class_name: str) -> None:
        """Validate that a class name doesn't already exist at module level.

        Args:
            class_name: The class name to validate

        Raises:
            ValueError: If the class name already exists at module level
        """
        checker = ClassConflictChecker(class_name)
        self.module.visit(checker)

        if checker.has_conflict:
            raise ValueError(f"Class '{class_name}' already exists in the module")

    def validate_constant_name(self, constant_name: str) -> None:
        """Validate that a constant name doesn't already exist at module level.

        Args:
            constant_name: The constant name to validate (typically UPPERCASE)

        Raises:
            ValueError: If the constant name already exists at module level
        """
        checker = ConstantConflictChecker(constant_name)
        self.module.visit(checker)

        if checker.has_conflict:
            raise ValueError(f"Constant '{constant_name}' already exists in the module")
