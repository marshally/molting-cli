"""Replace Type Code with State/Strategy refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_class_in_module, parse_target


class ReplaceTypeCodeWithStateStrategyCommand(BaseCommand):
    """Command to replace type code with State/Strategy pattern."""

    name = "replace-type-code-with-state-strategy"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "target" not in self.params:
            raise ValueError(
                "Missing required parameter for replace-type-code-with-state-strategy: 'target'"
            )
        if "name" not in self.params:
            raise ValueError(
                "Missing required parameter for replace-type-code-with-state-strategy: 'name'"
            )

    def execute(self) -> None:
        """Apply replace-type-code-with-state-strategy refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target = self.params["target"]
        new_class_name = self.params["name"]

        # Parse the target to get class and field names
        class_name, field_name = parse_target(target)

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = ReplaceTypeCodeWithStateStrategyTransformer(
            class_name, field_name, new_class_name
        )
        modified_tree = module.visit(transformer)

        self.file_path.write_text(modified_tree.code)


class ReplaceTypeCodeWithStateStrategyTransformer(cst.CSTTransformer):
    """Transforms type code into State/Strategy pattern."""

    def __init__(self, class_name: str, field_name: str, new_class_name: str) -> None:
        """Initialize the transformer.

        Args:
            class_name: Name of the class containing the type code
            field_name: Name of the field to replace
            new_class_name: Name of the new base class to create
        """
        self.class_name = class_name
        self.field_name = field_name
        self.new_class_name = new_class_name
        self.type_constants: list[tuple[str, int]] = []
        self.target_class: cst.ClassDef | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definitions to find target class.

        Args:
            node: The class definition node

        Returns:
            True to continue visiting children
        """
        if node.name.value == self.class_name:
            self.target_class = node
            # Extract type constants
            self._extract_type_constants(node)
        return True

    def _extract_type_constants(self, class_def: cst.ClassDef) -> None:
        """Extract type constants from class body.

        Args:
            class_def: The class definition
        """
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for body_item in stmt.body:
                    if isinstance(body_item, cst.Assign):
                        for target in body_item.targets:
                            if isinstance(target.target, cst.Name):
                                const_name = target.target.value
                                if isinstance(body_item.value, cst.Integer):
                                    const_value = int(body_item.value.value)
                                    self.type_constants.append((const_name, const_value))

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Add strategy classes and modify the target class.

        Args:
            original_node: The original module node
            updated_node: The updated module node

        Returns:
            Modified module
        """
        if not self.target_class:
            return updated_node

        # Create base class and subclasses
        new_classes = self._create_strategy_classes()

        # Find and modify the target class
        new_body: list[cst.BaseStatement] = []

        # Add strategy classes at the beginning
        for new_class in new_classes:
            new_body.append(new_class)
            # Add two empty lines after each class
            new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
            new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))

        # Add modified target class
        target_class_node = find_class_in_module(updated_node, self.class_name)
        for stmt in updated_node.body:
            if stmt is target_class_node and isinstance(stmt, cst.ClassDef):
                modified_class = self._modify_target_class(stmt)
                new_body.append(modified_class)
            else:
                new_body.append(stmt)

        return updated_node.with_changes(body=tuple(new_body))

    def _create_strategy_classes(self) -> list[cst.ClassDef]:
        """Create the base strategy class and subclasses.

        Returns:
            List of class definitions
        """
        classes: list[cst.ClassDef] = []

        # Create base class
        base_class = self._create_base_class()
        classes.append(base_class)

        # Create subclasses for each type constant
        for const_name, _ in self.type_constants:
            subclass = self._create_subclass(const_name)
            classes.append(subclass)

        return classes

    def _create_base_class(self) -> cst.ClassDef:
        """Create the base strategy class.

        Returns:
            Base class definition
        """
        # Create pay_amount method that raises NotImplementedError
        pay_amount_method = cst.FunctionDef(
            name=cst.Name("pay_amount"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(name=cst.Name("employee")),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(body=[cst.Raise(exc=cst.Name("NotImplementedError"))])
                ]
            ),
        )

        return cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[],
            body=cst.IndentedBlock(body=[pay_amount_method]),
        )

    def _create_subclass(self, const_name: str) -> cst.ClassDef:
        """Create a strategy subclass.

        Args:
            const_name: Name of the type constant

        Returns:
            Subclass definition
        """
        # Convert ENGINEER to Engineer
        class_name = const_name.title()

        # Find the method body by analyzing the conditional logic
        method_body = self._extract_method_body_for_type(const_name)

        pay_amount_method = cst.FunctionDef(
            name=cst.Name("pay_amount"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(name=cst.Name("employee")),
                ]
            ),
            body=cst.IndentedBlock(body=[method_body]),
        )

        return cst.ClassDef(
            name=cst.Name(class_name),
            bases=[cst.Arg(value=cst.Name(self.new_class_name))],
            body=cst.IndentedBlock(body=[pay_amount_method]),
        )

    def _extract_method_body_for_type(self, const_name: str) -> cst.BaseStatement:
        """Extract the method body for a specific type constant.

        Args:
            const_name: Name of the type constant

        Returns:
            Method body statement
        """
        if not self.target_class:
            return cst.SimpleStatementLine(body=[cst.Pass()])

        # Find the pay_amount method in the target class
        for stmt in self.target_class.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "pay_amount":
                # Parse the conditional logic
                return self._extract_return_for_type(stmt, const_name)

        return cst.SimpleStatementLine(body=[cst.Pass()])

    def _extract_return_for_type(
        self, method: cst.FunctionDef, const_name: str
    ) -> cst.BaseStatement:
        """Extract the return statement for a specific type.

        Args:
            method: The method containing conditional logic
            const_name: Name of the type constant

        Returns:
            Return statement
        """
        # Look through method body for If/Elif statements
        for stmt in method.body.body:
            if isinstance(stmt, cst.If):
                # Check the condition
                condition_matches = self._check_condition_matches_type(stmt.test, const_name)
                if condition_matches:
                    # Extract the return statement
                    return_stmt = self._extract_return_from_block(stmt.body)
                    if return_stmt:
                        # Replace self with employee
                        return self._replace_self_with_employee(return_stmt)

                # Check elif clauses
                current = stmt.orelse
                while current:
                    if isinstance(current, cst.If):
                        condition_matches = self._check_condition_matches_type(
                            current.test, const_name
                        )
                        if condition_matches:
                            return_stmt = self._extract_return_from_block(current.body)
                            if return_stmt:
                                return self._replace_self_with_employee(return_stmt)
                        current = current.orelse
                    else:
                        break

        return cst.SimpleStatementLine(body=[cst.Pass()])

    def _check_condition_matches_type(self, condition: cst.BaseExpression, const_name: str) -> bool:
        """Check if a condition matches the type constant.

        Args:
            condition: The condition expression
            const_name: Name of the type constant

        Returns:
            True if condition matches
        """
        if isinstance(condition, cst.Comparison):
            # Check for self.type == self.ENGINEER pattern
            if isinstance(condition.comparisons[0].comparator, cst.Attribute):
                attr = condition.comparisons[0].comparator
                if isinstance(attr.attr, cst.Name) and attr.attr.value == const_name:
                    return True

        return False

    def _extract_return_from_block(self, block: cst.BaseSuite) -> cst.SimpleStatementLine | None:
        """Extract return statement from a block.

        Args:
            block: The block to search

        Returns:
            Return statement or None
        """
        if isinstance(block, cst.IndentedBlock):
            for stmt in block.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for body_item in stmt.body:
                        if isinstance(body_item, cst.Return):
                            return stmt
        return None

    def _replace_self_with_employee(self, stmt: cst.SimpleStatementLine) -> cst.SimpleStatementLine:
        """Replace self with employee in a statement.

        Args:
            stmt: The statement to transform

        Returns:
            Modified statement
        """
        transformer = SelfToEmployeeTransformer()
        return cast(cst.SimpleStatementLine, stmt.visit(transformer))

    def _modify_target_class(self, class_def: cst.ClassDef) -> cst.ClassDef:
        """Modify the target class to use strategy pattern.

        Args:
            class_def: The class definition to modify

        Returns:
            Modified class definition
        """
        new_body: list[cst.BaseStatement] = []
        skip_next_empty_line = False

        for stmt in class_def.body.body:
            # Remove type constant definitions
            if self._is_type_constant_definition(stmt):
                # Skip empty lines after removed constants
                skip_next_empty_line = True
                continue

            # Skip empty line after removed constants
            if skip_next_empty_line and isinstance(stmt, cst.EmptyLine):
                skip_next_empty_line = False
                continue

            # Modify pay_amount method
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "pay_amount":
                modified_method = self._create_delegating_pay_amount()
                new_body.append(modified_method)
            elif isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Preserve __init__ but ensure blank line before pay_amount
                new_body.append(stmt)
                # Add blank line after __init__
                new_body.append(cast(cst.BaseStatement, cst.EmptyLine()))
            else:
                new_body.append(stmt)

        return class_def.with_changes(body=cst.IndentedBlock(body=new_body))

    def _is_type_constant_definition(self, stmt: cst.BaseStatement) -> bool:
        """Check if a statement is a type constant definition.

        Args:
            stmt: The statement to check

        Returns:
            True if it's a type constant definition
        """
        if isinstance(stmt, cst.SimpleStatementLine):
            for body_item in stmt.body:
                if isinstance(body_item, cst.Assign):
                    for target in body_item.targets:
                        if isinstance(target.target, cst.Name):
                            const_name = target.target.value
                            if any(const_name == name for name, _ in self.type_constants):
                                return True
        return False

    def _create_delegating_pay_amount(self) -> cst.FunctionDef:
        """Create a pay_amount method that delegates to the type object.

        Returns:
            Method definition
        """
        return cst.FunctionDef(
            name=cst.Name("pay_amount"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("self"), attr=cst.Name(self.field_name)
                                        ),
                                        attr=cst.Name("pay_amount"),
                                    ),
                                    args=[cst.Arg(value=cst.Name("self"))],
                                )
                            )
                        ]
                    )
                ]
            ),
        )


class SelfToEmployeeTransformer(cst.CSTTransformer):
    """Transforms self references to employee references."""

    def leave_Attribute(  # noqa: N802
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        """Replace self with employee in attribute access.

        Args:
            original_node: The original attribute node
            updated_node: The updated attribute node

        Returns:
            Modified attribute node
        """
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value == "self":
            return updated_node.with_changes(value=cst.Name("employee"))
        return updated_node


# Register the command
register_command(ReplaceTypeCodeWithStateStrategyCommand)
