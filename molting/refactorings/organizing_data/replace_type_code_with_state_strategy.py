"""Replace Type Code with State/Strategy pattern refactoring."""

import ast
from pathlib import Path
from typing import Dict, List

from molting.core.refactoring_base import RefactoringBase


class ReplaceTypeCodeWithStateStrategy(RefactoringBase):
    """Replace type code with State/Strategy pattern.

    Transforms code that uses type codes with if/elif chains into
    a State/Strategy pattern with separate classes for each type.
    """

    def __init__(self, file_path: str, target: str, name: str):
        """Initialize the refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target: Target field to replace (e.g., "Employee::type")
            name: Name for the base strategy class (e.g., "EmployeeType")
        """
        self.file_path = Path(file_path)
        self.target = target
        self.name = name
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the refactoring.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code
        """
        self.source = source

        if "::" not in self.target:
            raise ValueError(
                f"Target must be in format 'ClassName::field_name', got '{self.target}'"
            )

        class_name, field_name = self.target.split("::", 1)

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Find the target class
        target_class = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                target_class = node
                break

        if target_class is None:
            raise ValueError(f"Class '{class_name}' not found")

        # Extract type codes and method logic
        type_info = self._extract_type_info(target_class, field_name)

        if not type_info:
            raise ValueError(f"Could not extract type information for field '{field_name}'")

        # Create strategy classes
        strategy_classes = self._create_strategy_classes(type_info)

        # Modify the original class
        self._modify_original_class(target_class, field_name, type_info)

        # Insert strategy classes before the original class
        for i, strategy_class in enumerate(strategy_classes):
            tree.body.insert(i, strategy_class)

        ast.fix_missing_locations(tree)
        return ast.unparse(tree)

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        if "::" not in self.target:
            return False
        class_name, field_name = self.target.split("::", 1)
        return class_name in source and field_name in source

    def _extract_type_info(self, class_node: ast.ClassDef, field_name: str) -> Dict:
        """Extract type codes and their corresponding behavior.

        Args:
            class_node: The target class AST node
            field_name: Name of the type field

        Returns:
            Dictionary mapping type constants to strategy names and method logic
        """
        type_info = {}

        # Find class constants for type codes
        type_constants = {}
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(item.value, ast.Constant):
                            type_constants[target.id] = item.value.value

        # Find the pay_amount method or similar method with type-based logic
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                # Check if it has if/elif chains based on self.type
                method_logic = self._extract_method_logic(item, field_name, type_constants)
                if method_logic:
                    for const_name, logic in method_logic.items():
                        type_info[const_name] = {
                            "strategy_class": self._to_strategy_class_name(const_name),
                            "logic": logic,
                        }

        return type_info

    def _extract_method_logic(
        self, method: ast.FunctionDef, field_name: str, type_constants: Dict
    ) -> Dict:
        """Extract the logic for each type from conditional statements.

        Args:
            method: The method AST node
            field_name: Name of the type field
            type_constants: Mapping of constant names to values

        Returns:
            Dictionary mapping type constant names to their logic
        """
        method_logic = {}

        # Look for if/elif chains that check self.type
        for node in ast.walk(method):
            if isinstance(node, ast.If):
                logic = self._extract_if_chain_logic(node, field_name, type_constants)
                if logic:
                    method_logic.update(logic)

        return method_logic

    def _extract_if_chain_logic(
        self, if_node: ast.If, field_name: str, type_constants: Dict
    ) -> Dict:
        """Extract logic from if/elif chain.

        Args:
            if_node: The If AST node
            field_name: Name of the type field
            type_constants: Mapping of constant names to values

        Returns:
            Dictionary mapping type constant names to their return statements
        """
        logic = {}

        # Check the main if condition
        const_name = self._extract_type_constant_from_compare(if_node.test, field_name)
        if const_name:
            # Get the return statement from the if body
            for stmt in if_node.body:
                if isinstance(stmt, ast.Return) and stmt.value is not None:
                    # Transform self references to employee references
                    transformed_value = self._transform_self_to_employee(stmt.value)
                    logic[const_name] = transformed_value
                    break

        # Process elif and else
        for elif_node in if_node.orelse:
            if isinstance(elif_node, ast.If):
                const_name = self._extract_type_constant_from_compare(
                    elif_node.test, field_name
                )
                if const_name:
                    for stmt in elif_node.body:
                        if isinstance(stmt, ast.Return) and stmt.value is not None:
                            # Transform self references to employee references
                            transformed_value = self._transform_self_to_employee(stmt.value)
                            logic[const_name] = transformed_value
                            break
            elif isinstance(elif_node, ast.Return) and elif_node.value is not None:
                # This is an else with a return
                # Find the last type constant we saw
                if logic:
                    transformed_value = self._transform_self_to_employee(elif_node.value)
                    logic[list(logic.keys())[-1]] = transformed_value

        return logic

    def _extract_type_constant_from_compare(
        self, node: ast.expr, field_name: str
    ) -> str | None:
        """Extract type constant name from comparison.

        Args:
            node: The expression node
            field_name: Name of the type field

        Returns:
            Name of the type constant, or None if not found
        """
        if isinstance(node, ast.Compare):
            # Check if comparing self.type == CONSTANT
            if (
                len(node.ops) > 0
                and isinstance(node.ops[0], ast.Eq)
                and len(node.comparators) > 0
            ):

                left = node.left
                right = node.comparators[0]

                # Check if left is self.type or self.CONSTANT
                if isinstance(left, ast.Attribute):
                    if (
                        isinstance(left.value, ast.Name)
                        and left.value.id == "self"
                        and left.attr == field_name
                    ):
                        # Right should be the type constant
                        if isinstance(right, ast.Attribute):
                            if isinstance(right.value, ast.Name) and right.value.id == "self":
                                return right.attr
                        elif isinstance(right, ast.Name):
                            return right.id

        return None

    def _transform_self_to_employee(self, node: ast.expr) -> ast.expr:
        """Transform self references to employee references in an expression.

        Args:
            node: The AST expression node

        Returns:
            The transformed expression with self -> employee
        """
        if node is None:
            return node

        # Create a copy of the node
        node_copy = ast.parse(ast.unparse(node)).body[0].value

        # Walk the tree and replace self with employee
        for child in ast.walk(node_copy):
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name) and child.value.id == "self":
                    child.value.id = "employee"

        return node_copy

    def _to_strategy_class_name(self, constant_name: str) -> str:
        """Convert constant name to strategy class name.

        Args:
            constant_name: The constant name (e.g., "ENGINEER")

        Returns:
            Strategy class name (e.g., "Engineer")
        """
        return constant_name.capitalize()

    def _create_strategy_classes(self, type_info: Dict) -> List[ast.ClassDef]:
        """Create strategy classes for each type.

        Args:
            type_info: Dictionary mapping type constants to their logic

        Returns:
            List of ClassDef nodes for each strategy
        """
        strategy_classes = []

        # Create base strategy class
        base_class = ast.ClassDef(
            name=self.name,
            bases=[],
            keywords=[],
            body=[
                ast.FunctionDef(
                    name="pay_amount",
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[
                            ast.arg(arg="self", annotation=None),
                            ast.arg(arg="employee", annotation=None),
                        ],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=[ast.Raise(exc=ast.Name(id="NotImplementedError", ctx=ast.Load()))],
                    decorator_list=[],
                    returns=None,
                )
            ],
            decorator_list=[],
        )
        strategy_classes.append(base_class)

        # Create concrete strategy classes
        for const_name, info in type_info.items():
            strategy_name = info["strategy_class"]
            logic = info["logic"]

            # Create method that returns the logic
            method = ast.FunctionDef(
                name="pay_amount",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[
                        ast.arg(arg="self", annotation=None),
                        ast.arg(arg="employee", annotation=None),
                    ],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=[ast.Return(value=logic)],
                decorator_list=[],
                returns=None,
            )

            strategy_class = ast.ClassDef(
                name=strategy_name,
                bases=[ast.Name(id=self.name, ctx=ast.Load())],
                keywords=[],
                body=[method],
                decorator_list=[],
            )
            strategy_classes.append(strategy_class)

        return strategy_classes

    def _modify_original_class(
        self, class_node: ast.ClassDef, field_name: str, type_info: Dict
    ) -> None:
        """Modify the original class to use strategy pattern.

        Args:
            class_node: The target class AST node
            field_name: Name of the type field
            type_info: Dictionary mapping type constants to strategy info
        """
        # Replace type code constants with strategy instances
        new_body: list[ast.stmt] = []
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                should_replace = False
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in type_info:
                        should_replace = True
                        break

                if should_replace:
                    # Replace with strategy instance assignment
                    const_name = (
                        item.targets[0].id if isinstance(item.targets[0], ast.Name) else None
                    )
                    if const_name and const_name in type_info:
                        strategy_name = type_info[const_name]["strategy_class"]
                        # Create new assignment: ENGINEER = Engineer()
                        new_item: ast.stmt = ast.Assign(
                            targets=[ast.Name(id=const_name, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Name(id=strategy_name, ctx=ast.Load()),
                                args=[],
                                keywords=[],
                            ),
                        )
                        new_body.append(new_item)
                else:
                    new_body.append(item)
            elif isinstance(item, ast.FunctionDef):
                # Replace the method body to call strategy
                if self._has_type_conditional(item, field_name):
                    # Replace with strategy call
                    new_item = self._create_strategy_caller(item, field_name)
                    new_body.append(new_item)
                else:
                    new_body.append(item)
            else:
                new_body.append(item)

        class_node.body = new_body

    def _has_type_conditional(self, method: ast.FunctionDef, field_name: str) -> bool:
        """Check if method has type-based conditionals.

        Args:
            method: The method AST node
            field_name: Name of the type field

        Returns:
            True if method contains type conditionals
        """
        for node in ast.walk(method):
            if isinstance(node, ast.If):
                if self._has_type_comparison(node.test, field_name):
                    return True
        return False

    def _has_type_comparison(self, node: ast.expr, field_name: str) -> bool:
        """Check if node compares self.type.

        Args:
            node: The expression node
            field_name: Name of the type field

        Returns:
            True if node compares self.type
        """
        if isinstance(node, ast.Compare):
            if isinstance(node.left, ast.Attribute):
                if (
                    isinstance(node.left.value, ast.Name)
                    and node.left.value.id == "self"
                    and node.left.attr == field_name
                ):
                    return True
        return False

    def _create_strategy_caller(self, method: ast.FunctionDef, field_name: str) -> ast.FunctionDef:
        """Create a new method that calls the strategy.

        Args:
            method: The original method AST node
            field_name: Name of the type field

        Returns:
            New method that delegates to strategy
        """
        # Create: return self.type.pay_amount(self)
        return ast.FunctionDef(
            name=method.name,
            args=method.args,
            body=[
                ast.Return(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Attribute(
                                value=ast.Name(id="self", ctx=ast.Load()),
                                attr=field_name,
                                ctx=ast.Load(),
                            ),
                            attr=method.name,
                            ctx=ast.Load(),
                        ),
                        args=[ast.Name(id="self", ctx=ast.Load())],
                        keywords=[],
                    )
                )
            ],
            decorator_list=[],
            returns=None,
        )
