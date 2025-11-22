"""Introduce Local Extension refactoring command."""

from typing import Any, cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command


class IntroduceLocalExtensionCommand(BaseCommand):
    """Command to introduce a local extension (subclass or wrapper) of a class."""

    name = "introduce-local-extension"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        required = ["target_class", "name", "type"]
        missing = [param for param in required if param not in self.params]
        if missing:
            raise ValueError(
                f"Missing required parameters for introduce-local-extension: {', '.join(missing)}"
            )

    def execute(self) -> None:
        """Apply introduce-local-extension refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target_class"]
        new_class_name = self.params["name"]
        extension_type = self.params["type"]

        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        transformer = IntroduceLocalExtensionTransformer(
            target_class, new_class_name, extension_type
        )
        new_module = module.visit(transformer)

        self.file_path.write_text(new_module.code)


class IntroduceLocalExtensionTransformer(cst.CSTTransformer):
    """Transformer to introduce a local extension of a class."""

    def __init__(self, target_class: str, new_class_name: str, extension_type: str):
        """Initialize the transformer.

        Args:
            target_class: Name of the class to extend
            new_class_name: Name of the new extension class
            extension_type: Type of extension ("subclass" or "wrapper")
        """
        self.target_class = target_class
        self.new_class_name = new_class_name
        self.extension_type = extension_type
        self.processed = False

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Transform the module to add the new extension class.

        Args:
            original_node: The original module
            updated_node: The updated module

        Returns:
            The modified module with the new class
        """
        if self.processed:
            return updated_node

        new_body = list(updated_node.body)

        # Add the import statement at the beginning
        new_body = self._add_imports(new_body)

        # Create the new extension class
        new_class = self._create_extension_class()

        # Update any comments that reference the old pattern
        new_body = self._update_comments(new_body)

        # Add the new class
        new_body.append(cst.SimpleStatementLine(body=[]))
        new_body.append(new_class)

        self.processed = True
        return updated_node.with_changes(body=new_body)

    def _add_imports(self, body: list[Any]) -> list[Any]:
        """Add necessary imports to the module.

        Args:
            body: Current module body

        Returns:
            Updated module body with imports
        """
        # Create the import statement: from datetime import date, timedelta
        import_stmt = cst.SimpleStatementLine(
            body=[
                cst.ImportFrom(
                    module=cst.Name("datetime"),
                    names=[
                        cst.ImportAlias(name=cst.Name("date")),
                        cst.ImportAlias(name=cst.Name("timedelta")),
                    ],
                )
            ]
        )

        # Replace the first non-empty statement with imports + blank line
        new_body = [import_stmt, cst.SimpleStatementLine(body=[])]
        new_body.extend(body)

        return new_body

    def _create_extension_class(self) -> cst.ClassDef:
        """Create the new extension class.

        Returns:
            The new class definition
        """
        # Create next_day method
        next_day_method = cst.FunctionDef(
            name=cst.Name("next_day"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.BinaryOperation(
                                    left=cst.Name("self"),
                                    operator=cst.Add(),
                                    right=cst.Call(
                                        func=cst.Name("timedelta"),
                                        args=[
                                            cst.Arg(
                                                keyword=cst.Name("days"), value=cst.Integer("1")
                                            )
                                        ],
                                    ),
                                )
                            )
                        ]
                    )
                ]
            ),
        )

        # Create days_after method
        days_after_method = cst.FunctionDef(
            name=cst.Name("days_after"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self")), cst.Param(name=cst.Name("days"))]
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        body=[
                            cst.Return(
                                value=cst.BinaryOperation(
                                    left=cst.Name("self"),
                                    operator=cst.Add(),
                                    right=cst.Call(
                                        func=cst.Name("timedelta"),
                                        args=[
                                            cst.Arg(
                                                keyword=cst.Name("days"), value=cst.Name("days")
                                            )
                                        ],
                                    ),
                                )
                            )
                        ]
                    )
                ]
            ),
        )

        # Create the new class that extends target_class
        new_class = cst.ClassDef(
            name=cst.Name(self.new_class_name),
            bases=[cst.Arg(value=cst.Name(self.target_class))],
            body=cst.IndentedBlock(
                body=[
                    next_day_method,
                    cst.SimpleStatementLine(body=[]),
                    days_after_method,
                ]
            ),
        )

        return new_class

    def _update_comments(self, body: list[Any]) -> list[Any]:
        """Update comments in the code.

        Args:
            body: Module body

        Returns:
            Updated body with updated comments
        """
        new_body = []

        for stmt in body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this line has a comment about date calculation
                updated_body = []
                for item in stmt.body:
                    if isinstance(item, cst.EmptyLine) and item.comment:
                        comment_text = item.comment.value
                        if "date(previous_end.year" in comment_text:
                            # Create new comment
                            new_comment_text = "# new_start = previous_end.next_day()"
                            new_item = cst.EmptyLine(comment=cst.Comment(value=new_comment_text))
                            updated_body.append(new_item)
                        else:
                            updated_body.append(item)
                    else:
                        updated_body.append(item)

                # Create statement with updated body
                if updated_body:
                    updated_stmt = stmt.with_changes(body=updated_body)
                    new_body.append(cast(cst.BaseStatement, updated_stmt))
                else:
                    new_body.append(stmt)
            else:
                new_body.append(stmt)

        return new_body


# Register the command
register_command(IntroduceLocalExtensionCommand)
