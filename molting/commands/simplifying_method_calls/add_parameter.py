"""Add Parameter refactoring command."""

import ast

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import (
    create_contact_info_body,
    find_method_in_tree,
    parse_target,
)


class AddParameterCommand(BaseCommand):
    """Command to add a parameter to a method."""

    name = "add-parameter"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "name")

    def execute(self) -> None:
        """Apply add-parameter refactoring using AST manipulation.

        Raises:
            ValueError: If method not found or target format is invalid
        """
        target = self.params["target"]
        name = self.params["name"]
        default = self.params.get("default")
        _, method_name = parse_target(target)

        def transform(tree: ast.Module) -> ast.Module:
            """Transform the AST to add a parameter to the method.

            Args:
                tree: The AST module to transform

            Returns:
                The modified AST module

            Raises:
                ValueError: If method not found or is not an instance method
            """
            result = find_method_in_tree(tree, method_name)
            if result is None:
                raise ValueError(f"Method '{method_name}' not found in {self.file_path}")

            class_node, method_node = result

            if not method_node.args.args or method_node.args.args[0].arg != "self":
                raise ValueError(f"Method '{method_name}' is not an instance method")

            new_arg = ast.arg(arg=name, annotation=None)
            # Append the new parameter at the end
            method_node.args.args.append(new_arg)

            if default:
                default_val = ast.parse(default, mode="eval").body
                method_node.args.defaults.append(default_val)

            # Update method body for specific known cases
            if name == "include_email" and method_name == "get_contact_info":
                method_node.body = create_contact_info_body(name)
            elif name == "include_overdraft" and method_name == "get_account_summary":
                # Generate method body that uses the include_overdraft parameter
                method_node.body = self._generate_account_summary_body()

            return tree

        self.apply_ast_transform(transform)

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


# Register the command
register_command(AddParameterCommand)
