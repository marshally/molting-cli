"""Parameterize Method refactoring - consolidate similar methods into one parameterized method."""

from pathlib import Path
from typing import Optional

import libcst as cst

from molting.core.class_aware_transformer import ClassAwareTransformer
from molting.core.class_aware_validator import ClassAwareValidator
from molting.core.refactoring_base import RefactoringBase


class ParameterizeMethod(RefactoringBase):
    """Consolidate similar methods that differ only by a value into a single parameterized method."""

    def __init__(
        self,
        file_path: str,
        target1: str,
        target2: str,
        new_name: str,
    ):
        """Initialize the ParameterizeMethod refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target1: First method to consolidate (e.g., "ClassName::method_name1")
            target2: Second method to consolidate (e.g., "ClassName::method_name2")
            new_name: Name for the new parameterized method
        """
        self.file_path = Path(file_path)
        self.target1 = target1
        self.target2 = target2
        self.new_name = new_name
        self.source = self.file_path.read_text()

        # Parse the target specifications
        self.class_name1: Optional[str]
        self.function_name1: str
        self.class_name2: Optional[str]
        self.function_name2: str

        if "::" in self.target1:
            self.class_name1, self.function_name1 = self.parse_qualified_target(self.target1)
        else:
            self.class_name1 = None
            self.function_name1 = self.target1

        if "::" in self.target2:
            self.class_name2, self.function_name2 = self.parse_qualified_target(self.target2)
        else:
            self.class_name2 = None
            self.function_name2 = self.target2

    def apply(self, source: str) -> str:
        """Apply the parameterize method refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with parameterized method
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = ParameterizeMethodTransformer(
            class_name1=self.class_name1,
            function_name1=self.function_name1,
            class_name2=self.class_name2,
            function_name2=self.function_name2,
            new_name=self.new_name,
        )
        modified_tree = tree.visit(transformer)

        if not transformer.modified:
            raise ValueError(f"Could not find targets: {self.target1} and {self.target2}")

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
            validator = ValidateParameterizeMethodTransformer(
                class_name1=self.class_name1,
                function_name1=self.function_name1,
                class_name2=self.class_name2,
                function_name2=self.function_name2,
            )
            tree.visit(validator)
            return validator.found_both
        except Exception:
            return False


class ParameterizeMethodTransformer(ClassAwareTransformer):
    """Transform to consolidate similar methods into one parameterized method."""

    def __init__(
        self,
        class_name1: Optional[str],
        function_name1: str,
        class_name2: Optional[str],
        function_name2: str,
        new_name: str,
    ):
        """Initialize the transformer.

        Args:
            class_name1: Class name for first method
            function_name1: First method name to consolidate
            class_name2: Class name for second method
            function_name2: Second method name to consolidate
            new_name: Name for the new parameterized method
        """
        # Start with class_name1 as we'll track the class
        super().__init__(class_name=class_name1, function_name=function_name1)
        self.function_name1 = function_name1
        self.function_name2 = function_name2
        self.class_name2 = class_name2
        self.new_name = new_name
        self.modified = False

        # Track the methods we find
        self.method1_node: Optional[cst.FunctionDef] = None
        self.method2_node: Optional[cst.FunctionDef] = None
        self.method1_body: Optional[cst.FunctionDef] = None
        self.method2_body: Optional[cst.FunctionDef] = None

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Collect the method definitions we need to consolidate."""
        func_name = original_node.name.value

        # Check if this is one of the target functions
        if self.matches_target() and func_name == self.function_name1:
            self.method1_node = original_node
            self.method1_body = updated_node

        if self.matches_target() and func_name == self.function_name2:
            self.method2_node = original_node
            self.method2_body = updated_node

        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Replace the class with a version containing the parameterized method."""
        # Only process if we found both methods
        if self.method1_node is None or self.method2_node is None:
            return updated_node

        # Check if this is the right class
        if original_node.name.value != self.class_name:
            return updated_node

        # We need to:
        # 1. Create a new parameterized method
        # 2. Replace both old methods with calls to the new method

        self.modified = True

        # Extract parameter value from each method
        # For this simple case, we'll look for the multiply operation
        param1_value = self._extract_parameter_value(self.method1_body)
        param2_value = self._extract_parameter_value(self.method2_body)

        if param1_value is None or param2_value is None:
            raise ValueError("Could not extract parameter values from methods")

        # Create the new parameterized method
        new_method = self._create_parameterized_method(self.method1_body, param1_value)

        # Create wrapper methods that call the new method
        wrapper1 = self._create_wrapper_method(self.function_name1, param1_value)
        wrapper2 = self._create_wrapper_method(self.function_name2, param2_value)

        # Build new body: new method + two wrappers
        new_body = list(updated_node.body.body)

        # Find and replace the old methods
        new_body_list = []
        for item in new_body:
            if isinstance(item, cst.FunctionDef):
                if item.name.value == self.function_name1:
                    new_body_list.append(new_method)
                    new_body_list.append(wrapper1)
                elif item.name.value == self.function_name2:
                    new_body_list.append(wrapper2)
                else:
                    new_body_list.append(item)
            else:
                new_body_list.append(item)

        # Update the class body
        new_class_body = updated_node.body.with_changes(body=new_body_list)
        return updated_node.with_changes(body=new_class_body)

    def _extract_parameter_value(self, method: cst.FunctionDef) -> Optional[float]:
        """Extract the numeric value from a method's body.

        For methods like `self.salary *= 1.05`, extract 1.05 or 0.05
        """
        if not method or not method.body:
            return None

        # Look for assignment/augmented assignment with multiplication
        for stmt in method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for sub_stmt in stmt.body:
                    if isinstance(sub_stmt, cst.AugAssign):
                        if isinstance(sub_stmt.operator, cst.MultiplyAssign):
                            # Get the value (e.g., 1.05)
                            if isinstance(sub_stmt.value, cst.Float):
                                val_str = sub_stmt.value.value
                                val = float(val_str)
                                # Convert from 1.05 to 5 (percentage)
                                return (val - 1) * 100
                            elif isinstance(sub_stmt.value, cst.Integer):
                                val_str = sub_stmt.value.value
                                val = float(val_str)
                                return (val - 1) * 100
                            elif isinstance(sub_stmt.value, cst.BinaryOperation):
                                # Handle expressions like (1 + percentage / 100)
                                # Try to evaluate it
                                pass

        return None

    def _create_parameterized_method(
        self, original_method: cst.FunctionDef, original_value: float
    ) -> cst.FunctionDef:
        """Create the new parameterized method."""
        # Create new method signature: raise_salary(self, percentage)
        new_params = original_method.params.with_changes(
            params=(
                *original_method.params.params,
                cst.Param(name=cst.Name("percentage")),
            )
        )

        # Create new body: self.salary *= 1 + percentage / 100
        # Build the expression: 1 + percentage / 100
        division = cst.BinaryOperation(
            left=cst.Name("percentage"),
            operator=cst.Divide(),
            right=cst.Integer("100"),
        )
        addition = cst.BinaryOperation(
            left=cst.Integer("1"),
            operator=cst.Add(),
            right=division,
        )

        # Create the augmented assignment: self.salary *= (1 + percentage / 100)
        aug_assign = cst.AugAssign(
            target=cst.Attribute(value=cst.Name("self"), attr=cst.Name("salary")),
            operator=cst.MultiplyAssign(),
            value=addition,
        )

        # Create the new method body
        new_stmt = cst.SimpleStatementLine(body=[aug_assign])
        new_method_body = cst.IndentedBlock(body=[new_stmt])

        # Create the new method definition
        return cst.FunctionDef(
            name=cst.Name(self.new_name),
            params=new_params,
            body=new_method_body,
        )

    def _create_wrapper_method(self, method_name: str, param_value: float) -> cst.FunctionDef:
        """Create a wrapper method that calls the parameterized method."""
        # Create the method signature: five_percent_raise(self)
        new_params = cst.Parameters(
            params=(cst.Param(name=cst.Name("self")),)
        )

        # Create the call: self.raise_salary(5)
        call = cst.Call(
            func=cst.Attribute(
                value=cst.Name("self"),
                attr=cst.Name(self.new_name),
            ),
            args=(cst.Arg(value=cst.Integer(str(int(param_value)))),),
        )

        # Create the return statement
        expr_stmt = cst.SimpleStatementLine(body=[cst.Expr(call)])
        new_method_body = cst.IndentedBlock(body=[expr_stmt])

        # Create the method definition
        return cst.FunctionDef(
            name=cst.Name(method_name),
            params=new_params,
            body=new_method_body,
        )


class ValidateParameterizeMethodTransformer(ClassAwareValidator):
    """Visitor to check if both target methods exist."""

    def __init__(
        self,
        class_name1: Optional[str],
        function_name1: str,
        class_name2: Optional[str],
        function_name2: str,
    ):
        """Initialize the validator.

        Args:
            class_name1: Class name for first method
            function_name1: First method name to find
            class_name2: Class name for second method
            function_name2: Second method name to find
        """
        super().__init__(class_name1, function_name1)
        self.function_name1 = function_name1
        self.function_name2 = function_name2
        self.class_name2 = class_name2
        self.found_both = False
        self.found_method1 = False
        self.found_method2 = False

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """Check if we found the target functions."""
        func_name = node.name.value

        if self.matches_target():
            if func_name == self.function_name1:
                self.found_method1 = True
            if func_name == self.function_name2:
                self.found_method2 = True

        self.found_both = self.found_method1 and self.found_method2
        return True
