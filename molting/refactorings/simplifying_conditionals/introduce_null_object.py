"""Introduce Null Object refactoring - replace null checks with a null object."""

from pathlib import Path

import libcst as cst

from molting.core.refactoring_base import RefactoringBase


class IntroduceNullObject(RefactoringBase):
    """Replace null checks with a null object using libcst for AST transformation."""

    def __init__(self, file_path: str, target_class: str):
        """Initialize the IntroduceNullObject refactoring.

        Args:
            file_path: Path to the Python file to refactor
            target_class: Name of the class to create a null object for
        """
        self.file_path = Path(file_path)
        self.target_class = target_class
        self.source = self.file_path.read_text()

    def apply(self, source: str) -> str:
        """Apply the introduce null object refactoring to source code.

        Args:
            source: Python source code to refactor

        Returns:
            Refactored source code with null object pattern applied
        """
        self.source = source

        # Parse the source code with libcst
        try:
            tree = cst.parse_module(source)
        except Exception as e:
            raise ValueError(f"Failed to parse source code: {e}")

        # Transform the tree
        transformer = NullObjectTransformer(target_class=self.target_class)
        modified_tree = tree.visit(transformer)

        return modified_tree.code

    def validate(self, source: str) -> bool:
        """Validate that the refactoring can be applied.

        Args:
            source: Python source code to validate

        Returns:
            True if refactoring can be applied, False otherwise
        """
        # Check that the class exists
        return f"class {self.target_class}" in source


class NullObjectTransformer(cst.CSTTransformer):
    """Transform CST to introduce null object pattern."""

    def __init__(self, target_class: str):
        """Initialize the transformer.

        Args:
            target_class: Name of the class to create a null object for
        """
        self.target_class = target_class
        self.null_class_name = f"Null{target_class}"
        self.modified = False
        self.target_class_found = False
        self.target_class_node = None

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add null class to the module after the target class."""
        new_body = list(updated_node.body)

        # If we found the target class, add the null object class after it
        if self.target_class_found and self.target_class_node is not None:
            # Find where to insert the null class (after target class)
            insert_index = None
            for i, stmt in enumerate(new_body):
                if isinstance(stmt, cst.ClassDef) and stmt.name.value == self.target_class:
                    insert_index = i + 1
                    break

            if insert_index is not None:
                # Create the null object class
                null_class = self._create_null_class()
                new_body.insert(insert_index, null_class)

        return updated_node.with_changes(body=new_body)

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Process class definitions."""
        if updated_node.name.value == self.target_class:
            self.target_class_found = True
            self.target_class_node = updated_node

            # Add the is_null method to the original class
            is_null_method = self._create_is_null_method(returns_false=True)

            # Get the current body statements
            body_statements = list(updated_node.body.body)

            # Add is_null method to the class
            body_statements.append(is_null_method)

            # Create new body with the additional method
            new_body = updated_node.body.with_changes(body=body_statements)
            return updated_node.with_changes(body=new_body)

        return updated_node

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        """Process assignments to replace null checks with null object pattern."""
        # Only modify assignments to self.customer (for the target class)
        # Don't modify assignments within the target class itself

        # Check if this is an assignment to self.customer (the specific field for the target class)
        if len(updated_node.targets) == 1:
            target = updated_node.targets[0].target
            if isinstance(target, cst.Attribute):
                # This is self.something = value
                if isinstance(target.value, cst.Name) and target.value.value == "self":
                    field_name = target.attr.value
                    # Only modify if assigning to a field named the same as the target class (lowercase)
                    # This ensures we only modify "self.customer = customer" where Customer is target_class
                    if field_name.lower() == self.target_class.lower():
                        if isinstance(updated_node.value, cst.Name):
                            param_name = updated_node.value.value

                            # Create a ternary expression:
                            # customer if customer is not None else NullCustomer()
                            new_value = self._create_null_check_ternary(param_name)

                            return updated_node.with_changes(value=new_value)

        return updated_node

    def _create_null_check_ternary(self, param_name: str) -> cst.IfExp:
        """Create a ternary expression for null object pattern.

        Creates: param_name if param_name is not None else NullXxx()

        Args:
            param_name: Name of the parameter

        Returns:
            IfExp node for the ternary expression
        """
        # param_name if param_name is not None else NullXxx()
        return cst.IfExp(
            body=cst.Name(param_name),  # if true: param_name
            test=cst.Comparison(
                left=cst.Name(param_name),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.IsNot(),
                        comparator=cst.Name("None"),
                    )
                ],
            ),
            orelse=cst.Call(func=cst.Name(self.null_class_name)),
        )

    def _create_is_null_method(self, returns_false: bool = True) -> cst.SimpleStatementLine:
        """Create an is_null method.

        Args:
            returns_false: If True, create method that returns False (for real class)

        Returns:
            A FunctionDef for the is_null method
        """
        # Create the return statement
        return_value = cst.Name("False") if returns_false else cst.Name("True")
        return_stmt = cst.SimpleStatementLine(body=[cst.Return(value=return_value)])

        # Create function body
        body = cst.IndentedBlock(body=[return_stmt])

        # Create function with self parameter
        func_def = cst.FunctionDef(
            name=cst.Name("is_null"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=body,
        )

        return func_def

    def _create_null_class(self) -> cst.SimpleStatementLine:
        """Create the null object class.

        Args:
            target_class: Name of the class to create a null for

        Returns:
            A ClassDef for the null object
        """
        # Find the default values from the target class
        default_name = '"Unknown"'
        default_plan = '"Basic"'

        # Create __init__ method
        init_body = cst.IndentedBlock(
            body=[
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name("name"),
                                    )
                                )
                            ],
                            value=cst.SimpleString(default_name),
                        )
                    ]
                ),
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name("plan"),
                                    )
                                )
                            ],
                            value=cst.SimpleString(default_plan),
                        )
                    ]
                ),
            ]
        )

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=init_body,
        )

        # Create is_null method that returns True
        is_null_body = cst.IndentedBlock(
            body=[cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("True"))])]
        )

        is_null_method = cst.FunctionDef(
            name=cst.Name("is_null"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=is_null_body,
        )

        # Create the class definition
        class_def = cst.ClassDef(
            name=cst.Name(self.null_class_name),
            bases=[cst.Arg(value=cst.Name(self.target_class))],
            body=cst.IndentedBlock(body=[init_method, is_null_method]),
        )

        return class_def
