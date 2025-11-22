"""Introduce Local Extension refactoring command."""

from typing import Any

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

        # Create the imports needed
        new_body = self._add_imports(list(updated_node.body))

        # Create the new extension class
        new_class = self._create_extension_class()

        # Update comments in the code
        new_body = self._update_comments(new_body)

        # Add the new class at the end
        new_body.append(cst.SimpleStatementLine(body=[]))  # Empty line for spacing
        new_body.append(new_class)
        new_body.append(cst.SimpleStatementLine(body=[]))  # Empty line

        self.processed = True
        return updated_node.with_changes(body=new_body)

    def _add_imports(self, body: list[Any]) -> list[Any]:
        """Add necessary imports to the module.

        Args:
            body: Current module body

        Returns:
            Updated module body with imports
        """
        # Check if imports already exist
        has_datetime_import = False
        has_date_import = False
        has_timedelta_import = False

        for stmt in body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.ImportFrom):
                        if isinstance(item.module, cst.Attribute):
                            if isinstance(item.module.value, cst.Name):
                                if item.module.value.value == "datetime":
                                    # Check what's imported
                                    if item.names and not isinstance(item.names, cst.ImportStar):
                                        imported_names = [n.name.value for n in item.names]
                                        if "date" in imported_names:
                                            has_date_import = True
                                        if "timedelta" in imported_names:
                                            has_timedelta_import = True

        # If we need to add imports
        if not (has_datetime_import and has_date_import and has_timedelta_import):
            # Create import statement: from datetime import date, timedelta
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

            # Check if there's already an import section
            new_body = []
            import_added = False

            for stmt in body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    has_import = False
                    for item in stmt.body:
                        if isinstance(item, (cst.Import, cst.ImportFrom)):
                            has_import = True
                            break
                    if has_import:
                        new_body.append(stmt)
                        if not import_added:
                            new_body.append(import_stmt)
                            new_body.append(cst.SimpleStatementLine(body=[]))
                            import_added = True
                    else:
                        new_body.append(stmt)
                else:
                    new_body.append(stmt)

            if not import_added:
                new_body.insert(0, import_stmt)
                new_body.insert(1, cst.SimpleStatementLine(body=[]))

            return new_body

        return body

    def _create_extension_class(self) -> cst.ClassDef:
        """Create the new extension class.

        Returns:
            The new class definition
        """
        # Create methods for the extension
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

        # Create the new class
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
        """Update comments to use the new extension methods.

        Args:
            body: Module body

        Returns:
            Updated body with updated comments
        """
        new_body = []

        for stmt in body:
            if isinstance(stmt, cst.SimpleStatementLine):
                updated_stmt = stmt
                for item in stmt.body:
                    if isinstance(item, cst.EmptyLine):
                        # Check if there's a comment
                        if item.comment:
                            comment_text = item.comment.value
                            if "date(previous_end.year" in comment_text:
                                # Replace the old calculation comment
                                new_comment = "# new_start = previous_end.next_day()"
                                new_stmt = cst.SimpleStatementLine(
                                    body=[
                                        cst.EmptyLine(
                                            comment=cst.Comment(value=new_comment),
                                            whitespace=cst.SimpleWhitespace(""),
                                        )
                                    ]
                                )
                                new_body.append(new_stmt)
                                continue

                new_body.append(updated_stmt)
            else:
                new_body.append(stmt)

        return new_body


# Register the command
register_command(IntroduceLocalExtensionCommand)
