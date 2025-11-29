"""Introduce Null Object refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceNullObjectCommand(BaseCommand):
    """Replace null/None checks with a special null object that provides default behavior.

    The Introduce Null Object refactoring eliminates conditional checks for null values by
    creating a special subclass that implements the same interface but provides neutral default
    behavior. Instead of checking if an object is None throughout your code, you use a null
    object that "does nothing" or returns appropriate defaults, removing the need for guards.

    **When to use:**
    - You have frequent null checks (if x is None or if x is not None) scattered throughout code
    - You're checking the same object for nullness in many places
    - You want to simplify conditionals and reduce branching complexity
    - You have methods that would be called on both real objects and null cases
    - Your code suffers from "null pointer exception" handling patterns

    **Example:**

    Before:
        class Customer:
            def __init__(self, name: str, plan: str):
                self.name = name
                self.plan = plan

        class Site:
            def __init__(self, customer: Customer | None):
                if customer is not None:
                    self.customer = customer
                else:
                    self.customer = None

        def get_plan() -> str:
            if site.customer is not None:
                return site.customer.plan
            else:
                return "Unknown"

    After:
        class Customer:
            def __init__(self, name: str, plan: str):
                self.name = name
                self.plan = plan

            def is_null(self) -> bool:
                return False

        class NullCustomer(Customer):
            def __init__(self):
                self.name = "Unknown"
                self.plan = "Basic"

            def is_null(self) -> bool:
                return True

        class Site:
            def __init__(self, customer: Customer | None):
                self.customer = customer if customer is not None else NullCustomer()

        def get_plan() -> str:
            return site.customer.plan
    """

    name = "introduce-null-object"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target_class", "defaults")

    def _parse_defaults(self, defaults_str: str) -> dict[str, str]:
        """Parse defaults parameter into a dictionary.

        Args:
            defaults_str: Comma-separated key=value pairs, e.g., "name=Unknown,plan=Basic"

        Returns:
            Dictionary mapping field names to their default values
        """
        result: dict[str, str] = {}
        for pair in defaults_str.split(","):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    def execute(self) -> None:
        """Apply introduce-null-object refactoring using libCST.

        Raises:
            ValueError: If target_class is not found
        """
        target_class = self.params["target_class"]
        defaults = self._parse_defaults(self.params["defaults"])

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        transformer = IntroduceNullObjectTransformer(target_class, defaults=defaults)
        modified_tree = module.visit(transformer)

        # Update comments in the code
        code_text = modified_tree.code
        code_text = code_text.replace(
            "# Client code would check: if customer is not None",
            "# Client code no longer needs null checks",
        )

        self.file_path.write_text(code_text)


class IntroduceNullObjectTransformer(cst.CSTTransformer):
    """Transformer to introduce null object pattern."""

    def __init__(self, target_class: str, *, defaults: dict[str, str]) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to create null object for
            defaults: Dictionary mapping field names to their default values for the null object
        """
        self.target_class = target_class
        self.null_class_name = f"Null{target_class}"
        self.defaults = defaults
        self.target_class_node: cst.ClassDef | None = None
        self.instance_vars: dict[str, str] = {}  # Maps var name to default value
        self.current_class: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> None:  # noqa: N802
        """Capture the target class definition to extract information."""
        self.current_class = node.name.value
        if node.name.value == self.target_class:
            self.target_class_node = node
            self._extract_instance_vars(node)

    def _extract_instance_vars(self, node: cst.ClassDef) -> None:
        """Extract instance variable assignments from the class's __init__ method."""
        if not isinstance(node.body, cst.IndentedBlock):
            return

        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                if isinstance(stmt.body, cst.IndentedBlock):
                    for init_stmt in stmt.body.body:
                        # Look for self.var = value assignments
                        if isinstance(init_stmt, cst.SimpleStatementLine):
                            for s in init_stmt.body:
                                if isinstance(s, cst.Assign):
                                    if len(s.targets) > 0:
                                        target = s.targets[0].target
                                        if isinstance(target, cst.Attribute):
                                            if (
                                                isinstance(target.value, cst.Name)
                                                and target.value.value == "self"
                                                and isinstance(target.attr, cst.Name)
                                            ):
                                                var_name = target.attr.value
                                                # Extract default value based on parameter defaults
                                                default_val = self._get_default_value(
                                                    var_name, s.value
                                                )
                                                self.instance_vars[var_name] = default_val

    def _get_default_value(self, var_name: str, value_node: cst.BaseExpression) -> str:
        """Get default value for a null object instance variable.

        Args:
            var_name: The variable name
            value_node: The value being assigned in __init__

        Returns:
            String representation of the default value
        """
        # Use the provided defaults dictionary
        if var_name in self.defaults:
            value = self.defaults[var_name]
            # Quote strings if not already quoted
            if not (value.startswith('"') or value.startswith("'")):
                return f'"{value}"'
            return value
        else:
            # Fallback: return None for any unknown field
            return "None"

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef | cst.FlattenSentinel[cst.ClassDef]:
        """Transform class and add is_null method and null object class."""
        if original_node.name.value == self.target_class:
            # Add is_null method to the target class
            updated_node = self._add_is_null_method(updated_node, returns_false=True)
            # Create the null object class
            null_class = self._create_null_object_class()
            return cst.FlattenSentinel([updated_node, null_class])

        # Check if this class uses the target class
        if self._class_uses_target_class(original_node):
            # Add null check in __init__
            updated_node = self._add_null_check_to_class_using_target(updated_node)
            # Replace null checks with is_null() calls throughout the class
            updated_node = self._replace_null_checks_with_is_null(updated_node)

        return updated_node

    def _add_is_null_method(self, node: cst.ClassDef, returns_false: bool) -> cst.ClassDef:
        """Add is_null method to a class.

        Args:
            node: The class to modify
            returns_false: If True, method returns False; otherwise returns True

        Returns:
            Modified class with is_null method
        """
        if not isinstance(node.body, cst.IndentedBlock):
            return node

        # Create is_null method
        is_null_method = cst.FunctionDef(
            name=cst.Name("is_null"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[cst.Return(value=cst.Name("False" if returns_false else "True"))]
                    )
                ]
            ),
            leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))],
        )

        # Add method to the end of the class body
        new_body = list(node.body.body) + [is_null_method]
        return node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _create_null_object_class(self) -> cst.ClassDef:
        """Create the null object class.

        Returns:
            The null object class definition
        """
        # Create __init__ method with default values
        init_body_stmts: list[cst.BaseStatement] = []
        for var_name, default_value in self.instance_vars.items():
            init_body_stmts.append(
                cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    target=cst.Attribute(
                                        value=cst.Name("self"),
                                        attr=cst.Name(var_name),
                                    )
                                )
                            ],
                            value=cst.parse_expression(default_value),
                        )
                    ]
                )
            )

        init_method = cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(body=init_body_stmts),
        )

        # Create is_null method
        is_null_method = cst.FunctionDef(
            name=cst.Name("is_null"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[cst.SimpleStatementLine(body=[cst.Return(value=cst.Name("True"))])]
            ),
            leading_lines=[cst.EmptyLine(whitespace=cst.SimpleWhitespace(""))],
        )

        # Create the null object class
        return cst.ClassDef(
            name=cst.Name(self.null_class_name),
            bases=[cst.Arg(value=cst.Name(self.target_class))],
            body=cst.IndentedBlock(body=[init_method, is_null_method]),
            leading_lines=[cst.EmptyLine(), cst.EmptyLine()],
        )

    def _class_uses_target_class(self, node: cst.ClassDef) -> bool:
        """Check if a class uses the target class as a parameter in __init__.

        Args:
            node: The class to check

        Returns:
            True if the class has a parameter matching the target class name
        """
        if not isinstance(node.body, cst.IndentedBlock):
            return False

        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Get parameter names (skip self)
                param_names = [
                    p.name.value for p in stmt.params.params[1:] if isinstance(p.name, cst.Name)
                ]
                # Check if any parameter matches typical naming for target class
                # (lowercase version or singular form)
                target_lower = self.target_class.lower()
                return any(
                    p == target_lower or p == target_lower + "_obj" or p == self.target_class
                    for p in param_names
                )
        return False

    def _add_null_check_to_class_using_target(self, node: cst.ClassDef) -> cst.ClassDef:
        """Add null check to a class's __init__ method when it uses the target class.

        Args:
            node: The class definition

        Returns:
            Modified class with null check in __init__
        """
        if not isinstance(node.body, cst.IndentedBlock):
            return node

        new_body = []
        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                # Modify the __init__ method
                stmt = self._modify_init_for_null_check(stmt)
            new_body.append(stmt)

        return node.with_changes(body=cst.IndentedBlock(body=new_body))

    def _modify_init_for_null_check(self, init_method: cst.FunctionDef) -> cst.FunctionDef:
        """Modify __init__ to add null check for target class parameters.

        Args:
            init_method: The original __init__ method

        Returns:
            Modified __init__ method with null check
        """
        if not isinstance(init_method.body, cst.IndentedBlock):
            return init_method

        # Get parameter names (skip self)
        param_names = [
            p.name.value for p in init_method.params.params[1:] if isinstance(p.name, cst.Name)
        ]

        # Find which parameter name corresponds to target class
        target_param_name = None
        target_lower = self.target_class.lower()
        for param in param_names:
            if (
                param == target_lower
                or param == target_lower + "_obj"
                or param == self.target_class
            ):
                target_param_name = param
                break

        if not target_param_name:
            return init_method

        new_body = []
        for stmt in init_method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check for assignments involving the target parameter
                new_stmt_body = []
                for s in stmt.body:
                    if isinstance(s, cst.Assign):
                        if len(s.targets) > 0:
                            target = s.targets[0].target
                            if isinstance(target, cst.Attribute):
                                if (
                                    isinstance(target.value, cst.Name)
                                    and target.value.value == "self"
                                    and isinstance(target.attr, cst.Name)
                                ):
                                    # Check if the value being assigned is the target parameter
                                    if (
                                        isinstance(s.value, cst.Name)
                                        and s.value.value == target_param_name
                                    ):
                                        # Replace with conditional assignment to null object
                                        new_assignment = cst.Assign(
                                            targets=s.targets,
                                            value=cst.IfExp(
                                                test=cst.Comparison(
                                                    left=cst.Name(target_param_name),
                                                    comparisons=[
                                                        cst.ComparisonTarget(
                                                            operator=cst.IsNot(
                                                                whitespace_before=cst.SimpleWhitespace(
                                                                    " "
                                                                ),
                                                                whitespace_after=cst.SimpleWhitespace(
                                                                    " "
                                                                ),
                                                            ),
                                                            comparator=cst.Name("None"),
                                                        )
                                                    ],
                                                ),
                                                body=cst.Name(target_param_name),
                                                orelse=cst.Call(
                                                    func=cst.Name(self.null_class_name), args=[]
                                                ),
                                            ),
                                        )
                                        new_stmt_body.append(new_assignment)
                                    else:
                                        new_stmt_body.append(s)
                                else:
                                    new_stmt_body.append(s)
                            else:
                                new_stmt_body.append(s)
                        else:
                            new_stmt_body.append(s)
                    else:
                        new_stmt_body.append(s)  # type: ignore[arg-type]
                stmt = stmt.with_changes(body=new_stmt_body)
            new_body.append(stmt)

        return init_method.with_changes(body=cst.IndentedBlock(body=new_body))

    def _replace_null_checks_with_is_null(self, node: cst.ClassDef) -> cst.ClassDef:
        """Replace 'x is not None' checks with 'not x.is_null()' calls.

        Args:
            node: The class to transform

        Returns:
            Modified class with null checks replaced
        """
        visitor = NullCheckReplacer(self._get_target_param_name(node))
        return node.visit(visitor)  # type: ignore[return-value]

    def _get_target_param_name(self, node: cst.ClassDef) -> str | None:
        """Get the parameter name for the target class in __init__.

        Args:
            node: The class definition

        Returns:
            The parameter name or None
        """
        if not isinstance(node.body, cst.IndentedBlock):
            return None

        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                param_names = [
                    p.name.value for p in stmt.params.params[1:] if isinstance(p.name, cst.Name)
                ]
                target_lower = self.target_class.lower()
                for param in param_names:
                    if (
                        param == target_lower
                        or param == target_lower + "_obj"
                        or param == self.target_class
                    ):
                        return param
        return None


class NullCheckReplacer(cst.CSTTransformer):
    """Visitor to replace null checks with is_null() calls."""

    def __init__(self, target_param_name: str | None) -> None:
        """Initialize the replacer.

        Args:
            target_param_name: The parameter name to look for in null checks
        """
        self.target_param_name = target_param_name

    def leave_If(self, original_node: cst.If, updated_node: cst.If) -> cst.If:  # noqa: N802
        """Replace 'x is not None' with 'not x.is_null()' in if conditions."""
        if not self.target_param_name:
            return updated_node

        # Check if this is checking for None
        test = updated_node.test
        if isinstance(test, cst.Comparison):
            # Check for "x is not None" pattern
            if (
                isinstance(test.left, cst.Attribute)
                and isinstance(test.left.value, cst.Name)
                and test.left.value.value == "self"
                and isinstance(test.left.attr, cst.Name)
                and test.left.attr.value == self.target_param_name
                and len(test.comparisons) == 1
                and isinstance(test.comparisons[0].operator, cst.IsNot)
                and isinstance(test.comparisons[0].comparator, cst.Name)
                and test.comparisons[0].comparator.value == "None"
            ):
                # Replace with "not self.target_param.is_null()"
                new_test = cst.UnaryOperation(
                    operator=cst.Not(whitespace_after=cst.SimpleWhitespace(" ")),
                    expression=cst.Call(
                        func=cst.Attribute(
                            value=cst.Attribute(
                                value=cst.Name("self"),
                                attr=cst.Name(self.target_param_name),
                            ),
                            attr=cst.Name("is_null"),
                        ),
                        args=[],
                    ),
                )
                return updated_node.with_changes(test=new_test)

        return updated_node


# Register the command
register_command(IntroduceNullObjectCommand)
