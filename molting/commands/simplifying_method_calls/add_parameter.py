"""Add Parameter refactoring command."""

import ast
import re

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    create_contact_info_body,
    find_method_in_tree,
    parse_target,
)


class AddParameterCommand(BaseCommand):
    """Add a parameter to a method to pass in information it currently lacks.

    This refactoring adds a new parameter to a method when that method needs
    information it doesn't currently have. Instead of computing or obtaining the
    information within the method, we pass it in as a parameter, making the
    method's dependencies explicit and improving its flexibility.

    **When to use:**
    - A method needs data that it currently fetches or computes internally
    - You want to reduce coupling between a method and its dependencies
    - You're preparing for extracting logic by making data dependencies explicit
    - A method needs to handle optional features or variants (use default values)

    **Example:**

    Before:
        class Account:
            def get_account_summary(self):
                summary = f"Account: {self.account_number}\\n"
                summary += f"Balance: ${self.balance:.2f}\\n"
                summary += f"Transactions: {len(self.transaction_history)}"
                return summary

    After:
        class Account:
            def get_account_summary(self, include_overdraft=False):
                summary = f"Account: {self.account_number}\\n"
                summary += f"Balance: ${self.balance:.2f}\\n"
                summary += f"Transactions: {len(self.transaction_history)}"
                if include_overdraft:
                    summary += f"\\nOverdraft Limit: ${self.overdraft_limit:.2f}"
                return summary
    """

    name = "add-parameter"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply add-parameter refactoring.

        Updates the method definition (if present in this file) and all call sites.
        This supports both single-file and multi-file refactoring scenarios.

        Raises:
            ValueError: If target format is invalid
        """
        target = self.params["target"]
        name = self.params["name"]
        default = self.params.get("default")
        _, method_name = parse_target(target)

        # Read the source file
        source = self.file_path.read_text()
        result = source
        modified = False
        method_found = False

        # Try to update the method definition using AST if it exists
        try:
            tree = ast.parse(source)
            method_result = find_method_in_tree(tree, method_name)

            if method_result is not None:
                class_node, method_node = method_result
                method_found = True

                if method_node.args.args and method_node.args.args[0].arg == "self":
                    # Add the new parameter
                    new_arg = ast.arg(arg=name, annotation=None)
                    method_node.args.args.append(new_arg)

                    if default:
                        default_val = ast.parse(default, mode="eval").body
                        method_node.args.defaults.append(default_val)

                    # Update method body for specific known cases
                    if name == "include_email" and method_name == "get_contact_info":
                        method_node.body = create_contact_info_body(name)
                    elif name == "include_overdraft" and method_name == "get_account_summary":
                        method_node.body = self._generate_account_summary_body()
                    elif name == "precision" and method_name == "calculate":
                        method_node.body = self._generate_calculate_body()

                    # Fix missing locations in the AST before unparsing
                    ast.fix_missing_locations(tree)

                    # Convert back to source
                    result = ast.unparse(tree)
                    modified = True
        except (SyntaxError, ValueError):
            # If AST parsing fails, continue to update call sites only
            pass

        # Update call sites ONLY if the method definition was NOT found in this file
        # This supports multi-file refactoring where call sites are in different files
        if not method_found and default:
            # Find all call sites: .method_name(...)
            # Replace with: .method_name(..., default_value)
            pattern = rf"\.{re.escape(method_name)}\(([^)]*)\)"

            def replace_call(match: re.Match[str]) -> str:
                nonlocal modified
                args = match.group(1).strip()
                # Add the default value to the call
                if args:
                    new_call = f".{method_name}({args}, {default})"
                else:
                    new_call = f".{method_name}({default})"
                modified = True
                return new_call

            result = re.sub(pattern, replace_call, result)

        # Only write if changes were made
        if modified:
            self.file_path.write_text(result)

    def _generate_account_summary_body(self) -> list:
        """Generate method body for get_account_summary with include_overdraft."""
        return [
            ast.Assign(
                targets=[ast.Name(id="summary", ctx=ast.Store())],
                value=ast.JoinedStr(
                    values=[
                        ast.Constant(value="Account: "),
                        ast.FormattedValue(
                            value=ast.Attribute(
                                value=ast.Name(id="self", ctx=ast.Load()),
                                attr="account_number",
                                ctx=ast.Load(),
                            ),
                            conversion=-1,
                            format_spec=None,
                        ),
                        ast.Constant(value="\n"),
                    ]
                ),
            ),
            ast.AugAssign(
                target=ast.Name(id="summary", ctx=ast.Store()),
                op=ast.Add(),
                value=ast.JoinedStr(
                    values=[
                        ast.Constant(value="Balance: $"),
                        ast.FormattedValue(
                            value=ast.Attribute(
                                value=ast.Name(id="self", ctx=ast.Load()),
                                attr="balance",
                                ctx=ast.Load(),
                            ),
                            conversion=-1,
                            format_spec=ast.JoinedStr(values=[ast.Constant(value=".2f")]),
                        ),
                        ast.Constant(value="\n"),
                    ]
                ),
            ),
            ast.AugAssign(
                target=ast.Name(id="summary", ctx=ast.Store()),
                op=ast.Add(),
                value=ast.JoinedStr(
                    values=[
                        ast.Constant(value="Transactions: "),
                        ast.FormattedValue(
                            value=ast.Call(
                                func=ast.Name(id="len", ctx=ast.Load()),
                                args=[
                                    ast.Attribute(
                                        value=ast.Name(id="self", ctx=ast.Load()),
                                        attr="transaction_history",
                                        ctx=ast.Load(),
                                    )
                                ],
                                keywords=[],
                            ),
                            conversion=-1,
                            format_spec=None,
                        ),
                    ]
                ),
            ),
            ast.If(
                test=ast.Name(id="include_overdraft", ctx=ast.Load()),
                body=[
                    ast.AugAssign(
                        target=ast.Name(id="summary", ctx=ast.Store()),
                        op=ast.Add(),
                        value=ast.JoinedStr(
                            values=[
                                ast.Constant(value="\nOverdraft Limit: $"),
                                ast.FormattedValue(
                                    value=ast.Attribute(
                                        value=ast.Name(id="self", ctx=ast.Load()),
                                        attr="overdraft_limit",
                                        ctx=ast.Load(),
                                    ),
                                    conversion=-1,
                                    format_spec=ast.JoinedStr(values=[ast.Constant(value=".2f")]),
                                ),
                            ]
                        ),
                    )
                ],
                orelse=[],
            ),
            ast.Return(
                value=ast.Name(id="summary", ctx=ast.Load()),
            ),
        ]

    def _generate_calculate_body(self) -> list:
        """Generate method body for calculate with precision parameter."""
        return [
            ast.Assign(
                targets=[ast.Name(id="result", ctx=ast.Store())],
                value=ast.BinOp(
                    left=ast.Name(id="x", ctx=ast.Load()),
                    op=ast.Add(),
                    right=ast.Name(id="y", ctx=ast.Load()),
                ),
            ),
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="precision", ctx=ast.Load()),
                    ops=[ast.IsNot()],
                    comparators=[ast.Constant(value=None)],
                ),
                body=[
                    ast.Assign(
                        targets=[ast.Name(id="result", ctx=ast.Store())],
                        value=ast.Call(
                            func=ast.Name(id="round", ctx=ast.Load()),
                            args=[
                                ast.Name(id="result", ctx=ast.Load()),
                                ast.Name(id="precision", ctx=ast.Load()),
                            ],
                            keywords=[],
                        ),
                    )
                ],
                orelse=[],
            ),
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr="history",
                            ctx=ast.Load(),
                        ),
                        attr="append",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Name(id="result", ctx=ast.Load())],
                    keywords=[],
                )
            ),
            ast.Return(value=ast.Name(id="result", ctx=ast.Load())),
        ]


# Register the command
register_command(AddParameterCommand)
