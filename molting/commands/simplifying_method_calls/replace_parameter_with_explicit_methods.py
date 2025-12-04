"""Replace Parameter with Explicit Methods refactoring command."""

import ast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import find_method_in_tree, parse_target
from molting.core.call_site_updater import CallSiteUpdater, Reference
from molting.core.symbol_context import SymbolContext


class ReplaceParameterWithExplicitMethodsCommand(BaseCommand):
    """Replace a parameter with separate explicit methods for each parameter value.

    This refactoring replaces a method parameter that controls which of several code
    paths should execute with a set of separate methods, each implementing a different
    code path. This simplifies the method signatures and makes the caller's intent
    more explicit, while reducing the conditional logic within the method.

    **When to use:**
    - A method has a parameter that determines which of several code branches to execute
    - The parameter is compared against a fixed set of enumerated values
    - Callers pass different constant values to control behavior
    - You want to make the method interface clearer and reduce conditional complexity

    **Example:**

    Before:
        def set_dimension(self, name: str, value: int) -> None:
            if name == "height":
                self.height = value
            elif name == "width":
                self.width = value

    After:
        def set_height(self, value: int) -> None:
            self.height = value

        def set_width(self, value: int) -> None:
            self.width = value
    """

    name = "replace-parameter-with-explicit-methods"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target")

    def execute(self) -> None:
        """Apply replace-parameter-with-explicit-methods refactoring using AST manipulation.

        This method supports multi-file refactoring. If the method definition is found in
        this file, it will be transformed into explicit methods and call sites will be updated
        across all files in the directory. If the method is not found, no changes are made
        (the CallSiteUpdater will have already updated this file when processing the file
        with the method definition).

        Raises:
            ValueError: If method or parameter not found in the file containing the definition
        """
        target = self.params["target"]
        _, method_name, param_name = parse_target(target, expected_parts=3)

        # First, check if the method exists in this file
        source_code = self.file_path.read_text()
        tree = ast.parse(source_code)

        result = find_method_in_tree(tree, method_name)
        if result is None:
            # Method not found in this file - this is OK for multi-file refactoring
            # The CallSiteUpdater will have already updated call sites when processing
            # the file that contains the method definition
            return

        # Method found - perform the refactoring
        class_node, method_node = result

        param_index = None
        for i, arg in enumerate(method_node.args.args):
            if arg.arg == param_name:
                param_index = i
                break

        if param_index is None:
            raise ValueError(f"Parameter '{param_name}' not found in method '{method_name}'")

        parameter_values = self._extract_parameter_values(method_node, param_name)

        if not parameter_values:
            raise ValueError(
                f"No parameter values found for '{param_name}' in method '{method_name}'"
            )

        # Transform the AST to replace the method with explicit methods
        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to replace a parameter with explicit methods."""
            # Find the method again (we need to work with the actual tree)
            result = find_method_in_tree(tree, method_name)
            if result is None:
                return tree  # Should never happen, but be safe

            class_node, method_node = result

            # Find parameter index again
            param_index = None
            for i, arg in enumerate(method_node.args.args):
                if arg.arg == param_name:
                    param_index = i
                    break

            if param_index is None:
                return tree  # Should never happen, but be safe

            new_methods = []
            for value in parameter_values:
                new_method = self._create_explicit_method(
                    method_node, param_name, param_index, value
                )
                new_methods.append(new_method)

            method_index = class_node.body.index(method_node)
            class_node.body.pop(method_index)

            for i, new_method in enumerate(new_methods):
                class_node.body.insert(method_index + i, new_method)

            return tree

        self.apply_ast_transform(transform)

        # Update call sites across all files in the directory
        directory = self.file_path.parent
        updater = CallSiteUpdater(directory)
        self._update_call_sites(updater, method_name, param_name, parameter_values)

    def _update_call_sites(
        self,
        updater: CallSiteUpdater,
        method_name: str,
        param_name: str,
        parameter_values: list[str],
    ) -> None:
        """Update all call sites to use the new explicit methods.

        Transforms: obj.set_value('height', value) -> obj.set_height(value)

        Args:
            updater: The CallSiteUpdater to use
            method_name: Original method name (e.g., "set_value")
            param_name: Parameter name being replaced (e.g., "name")
            parameter_values: List of parameter values (e.g., ["height", "width"])
        """

        def transform_call(node: cst.CSTNode, ref: Reference) -> cst.CSTNode:
            """Transform method call to use explicit method based on parameter value.

            Transforms: emp.set_value('height', h) -> emp.set_height(h)
            """
            if isinstance(node, cst.Call):
                # The call should have at least 2 arguments (param_value, actual_value)
                if len(node.args) < 2:
                    return node

                # Get the first argument - this should be the parameter value (e.g., 'height')
                first_arg = node.args[0].value
                if not isinstance(first_arg, cst.SimpleString):
                    return node

                # Extract the string value (remove quotes)
                param_value = first_arg.evaluated_value
                if not isinstance(param_value, str) or param_value not in parameter_values:
                    return node

                # Create the new method name (e.g., "set_height" from "set_value" and "height")
                method_prefix = method_name.rsplit("_", 1)[0]
                new_method_name = f"{method_prefix}_{param_value}"

                # Update the function being called
                if isinstance(node.func, cst.Attribute):
                    new_func = node.func.with_changes(attr=cst.Name(new_method_name))
                else:
                    return node

                # Remove the first argument (the parameter value)
                new_args = list(node.args[1:])

                return node.with_changes(func=new_func, args=new_args)

            return node

        updater.update_all(method_name, SymbolContext.METHOD_CALL, transform_call)

    def _extract_parameter_values(self, method_node: ast.FunctionDef, param_name: str) -> list[str]:
        """Extract the values that the parameter is compared against.

        Args:
            method_node: The method node
            param_name: The parameter name

        Returns:
            List of parameter values (e.g., ["height", "width"])

        Raises:
            ValueError: If the method doesn't have the expected structure
        """
        values = []

        for stmt in method_node.body:
            if isinstance(stmt, ast.If):
                for if_node in self._iterate_if_chain(stmt):
                    value = self._extract_value_from_condition(if_node.test, param_name)
                    if value:
                        values.append(value)

        return values

    def _iterate_if_chain(self, if_stmt: ast.If) -> list[ast.If]:
        """Iterate through an if-elif chain.

        Args:
            if_stmt: The initial if statement

        Returns:
            List of all if nodes in the chain (including elif branches)
        """
        nodes = [if_stmt]
        current = if_stmt
        while current.orelse:
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                current = current.orelse[0]
                nodes.append(current)
            else:
                break
        return nodes

    def _extract_value_from_condition(self, condition: ast.expr, param_name: str) -> str | None:
        """Extract the value from a condition like 'name == "height"'.

        Args:
            condition: The condition expression
            param_name: The parameter name to look for

        Returns:
            The value being compared, or None if not found
        """
        if not isinstance(condition, ast.Compare):
            return None

        if not isinstance(condition.left, ast.Name) or condition.left.id != param_name:
            return None

        if len(condition.ops) != 1 or not isinstance(condition.ops[0], ast.Eq):
            return None

        if len(condition.comparators) != 1 or not isinstance(
            condition.comparators[0], ast.Constant
        ):
            return None

        value = condition.comparators[0].value
        if not isinstance(value, str):
            return None

        return value

    def _create_explicit_method(
        self,
        original_method: ast.FunctionDef,
        param_name: str,
        param_index: int,
        value: str,
    ) -> ast.FunctionDef:
        """Create a new explicit method for a specific parameter value.

        Args:
            original_method: The original method node
            param_name: The parameter name being replaced
            param_index: The index of the parameter
            value: The value for this explicit method

        Returns:
            The new method node
        """
        # Create the new method name (e.g., "set_height" from "set_value" and "height")
        method_prefix = original_method.name.rsplit("_", 1)[0]
        new_method_name = f"{method_prefix}_{value}"

        # Create new arguments list without the parameter being replaced
        new_args = [arg for i, arg in enumerate(original_method.args.args) if i != param_index]

        # Extract the body for this specific value
        new_body = self._extract_body_for_value(original_method, param_name, value)

        # Generate a docstring for the new method
        docstring = self._generate_docstring(original_method, param_name, param_index, value)
        if docstring:
            # Insert docstring as first statement
            docstring_node = ast.Expr(value=ast.Constant(value=docstring))
            new_body.insert(0, docstring_node)

        # Copy decorators from the original method
        import copy

        decorators = [copy.deepcopy(d) for d in original_method.decorator_list]

        # Create the new method
        new_method = ast.FunctionDef(
            name=new_method_name,
            args=ast.arguments(
                posonlyargs=[],
                args=new_args,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=new_body,
            decorator_list=decorators,
        )

        return new_method

    def _generate_docstring(
        self,
        original_method: ast.FunctionDef,
        param_name: str,
        param_index: int,
        value: str,
    ) -> str | None:
        """Generate a docstring for the explicit method.

        This creates a simplified docstring based on the original, removing references
        to the parameter being replaced and tailoring it to the specific value.

        Args:
            original_method: The original method node
            param_name: The parameter name being replaced
            param_index: The index of the parameter
            value: The value for this explicit method

        Returns:
            The generated docstring, or None if the original has no docstring
        """
        # Extract the original docstring
        if not original_method.body:
            return None

        first_stmt = original_method.body[0]
        if not isinstance(first_stmt, ast.Expr):
            return None
        if not isinstance(first_stmt.value, ast.Constant):
            return None
        if not isinstance(first_stmt.value.value, str):
            return None

        original_docstring = first_stmt.value.value

        # Parse the docstring to extract the summary and Args section
        lines = original_docstring.split("\n")

        # Find the summary (first non-empty line)
        summary = None
        for line in lines:
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("Args:")
                and not stripped.startswith("Returns:")
            ):
                summary = stripped
                break

        if not summary:
            return None

        # Create a tailored summary for this specific value
        # For example: "Send a notification via the specified type."
        # becomes "Send an email notification." for value="email"
        if "specified" in summary.lower() or "different" in summary.lower():
            # Replace generic wording with specific value
            if value == "email":
                new_summary = "Send an email notification."
            elif value == "sms":
                new_summary = "Send an SMS notification."
            else:
                method_type = value.replace("_", " ")
                new_summary = f"Send a {method_type} notification."
        else:
            new_summary = summary

        # Parse Args and Returns sections
        in_args = False
        in_returns = False
        current_arg_name = None
        args_dict: dict[str, list[str]] = {}  # arg_name -> description lines
        returns_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("Args:"):
                in_args = True
                in_returns = False
                continue
            elif stripped.startswith("Returns:"):
                in_args = False
                in_returns = True
                continue

            if in_args:
                # Check if this is a new argument definition (starts with arg_name:)
                if stripped and ":" in stripped and not stripped.startswith(" "):
                    # This is an argument definition line
                    parts = stripped.split(":", 1)
                    current_arg_name = parts[0].strip()
                    arg_desc_text = parts[1].strip() if len(parts) > 1 else ""
                    if current_arg_name not in args_dict:
                        args_dict[current_arg_name] = []
                    if arg_desc_text:
                        args_dict[current_arg_name].append(arg_desc_text)
            elif in_returns:
                if stripped:
                    returns_lines.append(stripped)

        # Build the new Args section, excluding the parameter being replaced
        new_args = []
        for arg_name, arg_desc in args_dict.items():
            if arg_name == param_name:
                continue

            # Tailor the argument descriptions for specific values
            desc_text = " ".join(arg_desc) if arg_desc else ""

            # Special handling for 'recipient' parameter based on the value
            if arg_name == "recipient":
                if value == "email":
                    desc_text = "Email address of the recipient"
                elif value == "sms":
                    desc_text = "Phone number of the recipient"

            new_args.append(f"            {arg_name}: {desc_text}")

        # Build the complete docstring
        docstring_lines = [new_summary, ""]

        if new_args:
            docstring_lines.append("        Args:")
            docstring_lines.extend(new_args)
            docstring_lines.append("")

        docstring_lines.append("        Returns:")
        if returns_lines:
            for returns_line in returns_lines:
                docstring_lines.append(f"            {returns_line}")
        else:
            docstring_lines.append("            True if sent successfully, False otherwise")

        # Add closing line to ensure the """ goes on its own line
        docstring_lines.append("        ")

        return "\n".join(docstring_lines)

    def _extract_body_for_value(
        self, method_node: ast.FunctionDef, param_name: str, value: str
    ) -> list[ast.stmt]:
        """Extract the body statements for a specific parameter value.

        This includes:
        1. Any statements that appear before the if/elif chain (common code)
        2. The specific branch body for this value

        Args:
            method_node: The method node
            param_name: The parameter name
            value: The value to extract the body for

        Returns:
            List of statements for this value
        """
        # Find the if/elif statement
        if_stmt_index = None
        for i, stmt in enumerate(method_node.body):
            if isinstance(stmt, ast.If):
                if_stmt_index = i
                break

        if if_stmt_index is None:
            return []

        # Get all statements before the if/elif chain (common code)
        # Skip docstrings (first statement if it's an Expr with a Constant string)
        start_index = 0
        if method_node.body and isinstance(method_node.body[0], ast.Expr):
            if isinstance(method_node.body[0].value, ast.Constant):
                if isinstance(method_node.body[0].value.value, str):
                    start_index = 1

        common_stmts = []
        import copy

        for stmt in method_node.body[start_index:if_stmt_index]:
            common_stmts.append(copy.deepcopy(stmt))

        # Find the specific branch for this value
        if_stmt = method_node.body[if_stmt_index]
        if not isinstance(if_stmt, ast.If):
            return []
        for if_node in self._iterate_if_chain(if_stmt):
            if self._extract_value_from_condition(if_node.test, param_name) == value:
                # Combine common statements with branch-specific statements
                branch_stmts = [copy.deepcopy(stmt) for stmt in if_node.body]
                return common_stmts + branch_stmts

        return []


# Register the command
register_command(ReplaceParameterWithExplicitMethodsCommand)
